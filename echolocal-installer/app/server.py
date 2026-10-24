#!/usr/bin/env python3
"""EchoLocal Installer — Home Assistant ingress app that flashes an Echo Dot over USB.

The heavy lifting is done by echoctl (https://github.com/ygelfand/echolocal), which this app
downloads from its release channel and runs non-interactively. echoctl prints plain progress
lines when its stdout is not a terminal, which is exactly how it is run here.

The app is deliberately smarted-free: it lists devices with `adb devices -l`, asks for a name
and Wi-Fi details, and streams one `echoctl install` run to the browser over SSE.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import queue
import subprocess
import threading
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8099
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")

DATA_DIR = "/data"
BIN_DIR = os.path.join(DATA_DIR, "bin")
ECHOCTL = os.path.join(BIN_DIR, "echoctl")
VERSION_STAMP = os.path.join(BIN_DIR, "echoctl.version")
OPTIONS_FILE = os.path.join(DATA_DIR, "options.json")
# The most recent install log, persisted so it survives a second install or a restart.
LAST_LOG = os.path.join(DATA_DIR, "last-install.log")

REPO = "ygelfand/echolocal"
ASSET_BY_MACHINE = {
    "x86_64": "echolocal_linux_x86_64",
    "amd64": "echolocal_linux_x86_64",
    "aarch64": "echolocal_linux_arm64",
    "arm64": "echolocal_linux_arm64",
}

# The add-on container is rebuilt from scratch, but /data persists. adb must keep one identity
# across restarts, so its key lives on the persistent volume.
ADB_HOME = os.path.join(DATA_DIR, ".android")

# A Dot previously running EchoMuse leaves a file footprint on /data. These are the ONLY
# paths the "clean" option removes: files and directories, never a partition, and nothing
# the bootloader, the amonet unlock, TWRP or the radio calibration depend on.
ECHOMUSE_PATHS = (
    "/data/emos",        # emOS state: wpa.conf, boot.state, boot-good.img, last_kmsg.*, console.pw
    "/data/local/bin",   # EchoMuse firmware: server{,_a,_b} + start_server.sh
    "/data/adb",         # Magisk (FireOS-with-root flow)
    "/data/misc/wifi",   # stale Android Wi-Fi state EchoLocal does not use
)


def adb_env():
    env = os.environ.copy()
    env["HOME"] = DATA_DIR
    env["ANDROID_USER_HOME"] = ADB_HOME
    return env


class Hub:
    """Stores the current install log and fans events out to SSE subscribers."""

    def __init__(self):
        self._lock = threading.Lock()
        self._subs = []
        self.log = []
        self.status = "idle"
        self.result = {}
        self.busy = False
        self.last_error = ""

    def subscribe(self):
        with self._lock:
            q = queue.Queue()
            backlog = list(self.log)
            status = {"kind": "status", "status": self.status, **self.result}
            self._subs.append(q)
            return q, backlog, status

    def unsubscribe(self, q):
        with self._lock:
            if q in self._subs:
                self._subs.remove(q)

    def _publish(self, event):
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(event)
            except Exception:
                pass

    def log_line(self, line):
        line = str(line).rstrip("\n")
        if not line:
            return
        with self._lock:
            self.log.append(line)
            if len(self.log) > 8000:
                del self.log[: len(self.log) - 8000]
        if self.busy:  # persist install runs only; startup/download lines would pollute it
            try:
                with open(LAST_LOG, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError:
                pass  # best-effort: the in-memory panel log is unaffected
        self._publish({"kind": "log", "line": line})

    def set_status(self, status, **extra):
        with self._lock:
            self.status = status
            self.result.update(extra)
            self.busy = status == "running"
            if status == "failed" and "error" in extra:
                self.last_error = extra["error"]
        self._publish({"kind": "status", "status": self.status, **self.result})


hub = Hub()
_download_lock = threading.Lock()


# ------------------------------------------------ options / state ----------------
def read_options():
    try:
        with open(OPTIONS_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


# Known-good fallback if the GitHub latest-release lookup is unreachable, so a network blip
# never leaves the version unresolved and never blocks an install.
FALLBACK_VERSION = "0.0.9"
_LATEST = {"tag": FALLBACK_VERSION, "at": 0.0}
LATEST_TTL = 3600  # re-check upstream at most once an hour


def latest_release(fetch=True):
    """Newest stable upstream echoctl tag, cached for LATEST_TTL seconds.

    Uses GitHub's /releases/latest, which excludes prereleases and drafts. With fetch=False the
    cache is read without contacting GitHub so a state poll never blocks; the startup download
    thread warms the cache. On failure the last good tag (initially FALLBACK_VERSION) is kept and
    the lookup backs off for the TTL.
    """
    now = time.monotonic()
    if _LATEST["at"] and (now - _LATEST["at"]) < LATEST_TTL:
        return _LATEST["tag"]
    if not fetch:
        return _LATEST["tag"]
    try:
        data = json.loads(http_get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=30))
        tag = (data.get("tag_name") or "").strip()
        if tag:
            _LATEST.update(tag=tag, at=now)
            return tag
    except Exception:  # noqa: BLE001 - GitHub unreachable; fall through to the cached tag
        pass
    _LATEST["at"] = now  # back off for the TTL even on failure, to avoid hammering the API
    return _LATEST["tag"]


def wanted_version(fetch=True):
    """The echoctl version to install: 'latest' (the default) resolves to the newest stable upstream release; any other value pins to that exact tag (an escape hatch to roll back)."""
    opt = str(read_options().get("echoctl_version", "latest")).strip()
    if not opt or opt.lower() == "latest":
        return latest_release(fetch=fetch)
    return opt


def installed_version():
    try:
        with open(VERSION_STAMP, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def echoctl_ready(version):
    if not (os.path.isfile(ECHOCTL) and os.access(ECHOCTL, os.X_OK)):
        return False
    if installed_version() != version:
        return False
    return True


# ------------------------------------------------ download -------------------------
def http_get(url, timeout=180):
    req = urllib.request.Request(url, headers={"User-Agent": "echolocal-installer-addon/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def verify_checksum(asset, data, checksums):
    want = None
    for line in checksums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == asset:
            want = parts[0].lower()
            break
    if want is None:
        raise RuntimeError(f"{asset} is not listed in checksums.txt")
    got = hashlib.sha256(data).hexdigest()
    if got != want:
        raise RuntimeError(f"checksum mismatch for {asset}")


def ensure_echoctl(version):
    """Download and verify the pinned echoctl binary exactly once per version."""
    with _download_lock:
        if echoctl_ready(version):
            return
        machine = platform.machine()
        asset = ASSET_BY_MACHINE.get(machine)
        if not asset:
            raise RuntimeError(f"no echoctl build for architecture {machine!r}")
        base = f"https://github.com/{REPO}/releases/download/{version}"
        hub.log_line(f"Downloading {asset} ({version}) …")
        data = http_get(f"{base}/{asset}")
        try:
            sums = http_get(f"{base}/checksums.txt").decode("utf-8", "replace")
            verify_checksum(asset, data, sums)
            hub.log_line("Checksum verified against checksums.txt.")
        except Exception as exc:  # noqa: BLE001 - surface but do not block a user fix
            hub.log_line(f"WARNING: could not verify checksum: {exc}")
        os.makedirs(BIN_DIR, exist_ok=True)
        tmp = ECHOCTL + ".part"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.chmod(tmp, 0o755)
        os.replace(tmp, ECHOCTL)
        with open(VERSION_STAMP, "w", encoding="utf-8") as fh:
            fh.write(version)
        hub.log_line(f"Installed echoctl {version}.")


def _download_thread(version):
    try:
        ensure_echoctl(version)
    except Exception as exc:  # noqa: BLE001 - an install will surface this again
        hub.log_line(f"Download failed: {exc}")


# ------------------------------------------------ adb ------------------------------
def adb_devices():
    proc = subprocess.run(
        ["adb", "devices", "-l"],
        capture_output=True, text=True, env=adb_env(), timeout=30,
    )
    devices = []
    for raw in proc.stdout.splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        attrs = {}
        for token in parts[2:]:
            if ":" in token:
                key, _, value = token.partition(":")
                attrs[key] = value
        devices.append({
            "serial": serial,
            "state": state,
            "model": attrs.get("model", ""),
            "product": attrs.get("product", ""),
            "device": attrs.get("device", ""),
        })
    return devices


def adb_shell(serial, script, timeout=30):
    proc = subprocess.run(
        ["adb", "-s", serial, "shell", script],
        capture_output=True, text=True, env=adb_env(), timeout=timeout,
    )
    return proc.stdout.strip(), proc.returncode


# ------------------------------------------------ clean ---------------------------
def path_exists(serial, path):
    out, _ = adb_shell(serial, f"[ -e {path} ] && echo yes")
    return "yes" in out


def wipe_echomuse(serial):
    """Remove a previous EchoMuse install's leftovers on /data, before installing.

    File-level only: it deletes EchoMuse's own directories and never writes or erases a
    partition, so the bootloader, the amonet unlock, TWRP and the radio calibration are
    untouched by construction. Runs in TWRP with /data mounted; a failed removal is logged
    and the install continues rather than aborting.
    """
    hub.log_line("Cleaning previous install leftovers from /data …")
    # Make sure the userdata partition is mounted and writable so the paths resolve.
    adb_shell(serial, "twrp mount data >/dev/null 2>&1; mount /data >/dev/null 2>&1")
    for path in ECHOMUSE_PATHS:
        if path_exists(serial, path):
            hub.log_line(f"  removing {path}")
            adb_shell(serial, f"rm -rf {path}")
        else:
            hub.log_line(f"  {path} not present — skipped")
    left = [path for path in ECHOMUSE_PATHS if path_exists(serial, path)]
    if left:
        hub.log_line(f"WARNING: still present after clean: {' '.join(left)}")
    else:
        hub.log_line("No previous-install leftovers on /data.")


# ------------------------------------------------ install --------------------------
def redact(argv):
    """Do not put the Wi-Fi passphrase in the log."""
    out, hide = [], False
    for token in argv:
        if hide:
            out.append("********")
            hide = False
            continue
        out.append(token)
        if token == "--password":
            hide = True
    return out


def build_install_cmd(serial, name, ssid, password, reboot):
    cmd = [ECHOCTL, "install", "--serial", serial, "-y"]
    cmd.append("--reboot" if reboot else "--no-reboot")
    if name:
        cmd += ["--name", name]
    if ssid:
        cmd += ["--ssid", ssid]
        if password:
            cmd += ["--password", password]
    return cmd


def read_key(serial):
    """Read the pairing key after install; empty means the device is unprovisioned (zero-PSK)."""
    for args in (["key", "show"], ["key"]):
        try:
            proc = subprocess.run(
                [ECHOCTL, *args, "--serial", serial],
                capture_output=True, text=True, env=adb_env(), timeout=60,
            )
        except Exception:  # noqa: BLE001
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            out = proc.stdout.strip()
            if "unprovisioned" in out:
                return ""
            lines = [ln for ln in out.splitlines() if ln.strip()]
            if lines:
                return lines[-1]
    return ""


def run_install(payload):
    try:
        version = payload.get("version") or wanted_version()
        serial = (payload.get("serial") or "").strip()
        if not serial:
            raise RuntimeError("no device selected")
        reboot = bool(payload.get("reboot", True))
        name = (payload.get("name") or "").strip()
        ssid = (payload.get("ssid") or "").strip()
        password = payload.get("password") or ""

        hub.log_line("Starting adb server …")
        subprocess.run(["adb", "start-server"], capture_output=True, text=True,
                       env=adb_env(), timeout=30)

        known = {dev["serial"]: dev for dev in adb_devices()}
        dev = known.get(serial)
        if dev is None:
            raise RuntimeError(f"device {serial} is no longer connected")
        if dev["state"] not in ("device", "recovery"):
            raise RuntimeError(f"device {serial} is {dev['state']}; echoctl needs it 'device' or 'recovery'")

        ensure_echoctl(version)
        if payload.get("clean"):
            wipe_echomuse(serial)

        cmd = build_install_cmd(serial, name, ssid, password, reboot)
        hub.log_line("$ " + " ".join(redact(cmd)))
        hub.log_line("")

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env=adb_env(),
        )
        for line in proc.stdout:
            hub.log_line(line.rstrip("\n"))
        code = proc.wait()

        if code != 0:
            hub.log_line(f"echoctl exited with status {code}.")
            hub.set_status("failed", exit=code, key="")
            return

        key = read_key(serial)
        hub.log_line("")
        if key:
            hub.log_line("Pairing key: " + key)
        else:
            hub.log_line("No key on the device (zero-PSK provisioning) — Home Assistant can push one.")
        hub.set_status("done", exit=0, key=key)
    except Exception as exc:  # noqa: BLE001 - surfaced to the panel
        hub.log_line(f"ERROR: {exc}")
        hub.set_status("failed", exit=-1, key="", error=str(exc))


def start_install(payload):
    with hub._lock:
        if hub.busy:
            return False
        hub.log = []
        try:
            with open(LAST_LOG, "w", encoding="utf-8") as fh:
                fh.write(f"== install started {datetime.now().isoformat(timespec='seconds')} "
                         f"serial={payload.get('serial', '')} ==\n")
        except OSError:
            pass  # best-effort persistence
        hub.status = "running"
        hub.result = {}
        hub.busy = True
        hub.last_error = ""
    hub._publish({"kind": "reset"})
    hub._publish({"kind": "status", "status": "running"})
    threading.Thread(target=run_install, args=(payload,), daemon=True).start()
    return True


# ------------------------------------------------ http ------------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "EchoLocalInstaller/0.1"

    def log_message(self, fmt, *args):  # keep the app log quiet
        pass

    def _send(self, code, body=b"", ctype="text/plain; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def _sse(self, obj):
        data = json.dumps(obj).encode("utf-8")
        self.wfile.write(b"data: " + data + b"\n\n")
        self.wfile.flush()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(STATIC_DIR, "index.html"), "rb") as fh:
                    self._send(200, fh.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(500, b"index.html missing", "text/plain; charset=utf-8")
        elif path == "/api/state":
            version = wanted_version(fetch=False)
            self._json({
                "status": hub.status,
                "busy": hub.busy,
                "echoctl_version": version,
                "echoctl_latest": latest_release(fetch=False),
                "binary_ready": echoctl_ready(version),
                "arch": platform.machine(),
                "devices": [] if hub.busy else adb_devices(),
                "result": hub.result,
            })
        elif path == "/api/devices":
            self._json({"devices": adb_devices()})
        elif path == "/api/last-log":
            try:
                with open(LAST_LOG, "rb") as fh:
                    self._send(200, fh.read(), "text/plain; charset=utf-8")
            except OSError:
                self._send(200, b"", "text/plain; charset=utf-8")
        elif path == "/api/events":
            self._events()
        else:
            self._send(404, b"not found")

    def _read_body(self):
        """Read the request body, supporting both framing styles.

        Home Assistant's ingress proxy forwards browser POSTs with chunked
        transfer encoding (no Content-Length header), so reading only by
        Content-Length silently loses the whole payload — which surfaced as
        "no device selected" on every panel install. Support both.
        """
        if "chunked" in (self.headers.get("Transfer-Encoding", "") or "").lower():
            data = b""
            while True:
                size_line = self.rfile.readline().strip()
                size = int(size_line.split(b";")[0] or b"0", 16)
                if size == 0:
                    self.rfile.readline()  # trailing CRLF after the last chunk
                    break
                data += self.rfile.read(size)
                self.rfile.readline()  # CRLF after each chunk
            return data
        length = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(length) if length else b""

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        raw = self._read_body()
        if path == "/api/install":
            try:
                payload = json.loads(raw or b"{}")
            except Exception:  # noqa: BLE001
                payload = {}
            if start_install(payload):
                self._json({"started": True})
            else:
                self._json({"started": False, "error": "an install is already running"}, 409)
        elif path == "/api/download":
            threading.Thread(target=_download_thread, args=(wanted_version(),), daemon=True).start()
            self._json({"started": True})
        else:
            self._send(404, b"not found")

    def _events(self):
        q, backlog, status = hub.subscribe()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        self.close_connection = True
        try:
            self._sse(status)
            for line in backlog:
                self._sse({"kind": "log", "line": line})
            while True:
                try:
                    event = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                self._sse(event)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            hub.unsubscribe(q)


def main():
    os.makedirs(BIN_DIR, exist_ok=True)
    os.makedirs(ADB_HOME, exist_ok=True)
    version = wanted_version()
    hub.log_line("EchoLocal Installer ready.")
    hub.log_line(
        f"echoctl {version} ({'cached' if echoctl_ready(version) else 'not downloaded yet'})."
    )
    threading.Thread(target=_download_thread, args=(version,), daemon=True).start()

    server = ThreadingHTTPServer(("", PORT), Handler)
    server.daemon_threads = True
    print(f"EchoLocal Installer listening on :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()