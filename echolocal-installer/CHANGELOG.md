# Changelog

## 0.1.6 — 2026-10-18

- Follow upstream by default: `echoctl_version` now defaults to `latest`, resolving the newest
  **stable** ygelfand/echolocal release (prereleases/drafts excluded) at install time, so the
  add-on no longer goes stale when a new `echoctl` ships. An explicit tag still pins/rolls back,
  checksums are still verified, a known-good fallback covers a GitHub outage, and the panel badge
  shows the upstream version when it differs.

## 0.1.5 — 2026-10-18

- Bump the pinned `echoctl` to **0.0.9**, which includes the upstream fix for the `initRC` glob /
  dangling `/system_root/vendor` bug (ygelfand/echolocal#94).
- Remove the TWRP `vendor/etc/init` RAM-placeholder workaround (`apply_vendor_workaround`) —
  no longer needed now that a fixed `echoctl` is pinned.

## 0.1.4 — 2026-10-18

- Rename the clean option to **Clean previous install leftovers** — it also covers generic
  Magisk roots and skips paths that are not present. (The 0.1.3 wording shipped to hardware
  before the rename landed, which stranded it; hence this bump.)
- Persist each install log to `/data/last-install.log` (rewritten at the start of each
  install, so it always holds the most recent run) and serve it read-only at
  `GET /api/last-log`, so a completed run's log survives a second install or an add-on
  restart. Startup and download lines are not persisted, and the file carries the same
  redacted content as the panel (never the Wi-Fi passphrase).

## 0.1.3 — 2026-10-18

- Optional **Clean previous install leftovers** checkbox on the install form. When ticked,
  the add-on removes previous-install leftovers from `/data` (`/data/emos`,
  `/data/local/bin` — EchoMuse firmware, `/data/adb` — Magisk, `/data/misc/wifi` — stale
  Android Wi-Fi state) over `adb` in TWRP before invoking `echoctl install`. File-level only
  — it never writes or erases a partition, so the bootloader, the amonet unlock, TWRP and the
  radio calibration are untouched. Unticked by default; paths that are not present are skipped
  and a failed removal is logged without aborting the install.

## 0.1.2 — 2026-10-09

- Document the final pairing step (copy the key → Settings → Devices & Services → ESPHome →
  Configure → paste the encryption key) in the panel, README, and DOCS.md.

## 0.1.1 — 2026-10-09

- Fix the install POST body being lost through Home Assistant's ingress proxy (it uses chunked
  transfer encoding; the server only read Content-Length bodies), which made every panel install
  fail with "no device selected" regardless of the selected device.

## 0.1.0 — 2026-10-09

Initial release.

- Ingress panel that lists USB devices with `adb` and runs a pinned `echoctl install` with
  live log streaming.
- Downloads the pinned `echoctl` release binary for the host architecture and verifies the
  SHA-256 against the release's `checksums.txt`.
- Automatic TWRP `vendor/etc/init` placeholder workaround for the upstream `initRC` glob bug
  (issue #94); removed once a fixed `echoctl` release is pinned. See
  `docs/development/upstream-initrc-fix.md`.
- Installer only: no Wi-Fi reconfiguration, no uninstall, no entities.