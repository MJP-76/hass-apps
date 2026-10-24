# Decisions

Record of why this repository is the way it is. Newest last.

## D1 — An add-on, not an integration (2026-10-09)

Flashing an Echo Dot needs raw USB and `adb`. A Home Assistant **integration** runs in the
Core container, which has no USB access; a Supervisor **add-on** can request `usb: true`.
So the installer is an add-on with an Ingress panel.

Consequence: Home Assistant cannot "figuring out the USB side" for us unless it can see
`/dev/bus/usb`, which only the add-on can.

## D2 — Install only (2026-10-09)

The add-on installs EchoLocal and stops there. No Wi-Fi reconfiguration, no status polling,
no uninstall, and **no entities or devices registered in Home Assistant**. Adding a companion
integration later would be a separate decision.

## D3 — Pin `echoctl` to 0.0.8 (2026-10-09)

The add-on downloads the upstream `echoctl` release binary rather than embedding it, so it can
be bumped without rebuilding. 0.0.8 is the version this add-on is written and tested against;
the version is an add-on option (`echoctl_version`) so a future fix can be adopted without a
code change. Do **not** downgrade to 0.0.6 — 0.0.8 is the correct version for SDK 25.

## D4 — Carry the TWRP workaround until upstream is fixed (2026-10-09)

`echoctl` 0.0.8 aborts on Fire OS 6 when a shell glob matches nothing: `/system_root/vendor` is
an absolute symlink to `/system/vendor`, which in TWRP resolves into an empty rootfs, so
`vendor/etc/init/*.rc` matches nothing, `ls` exits non-zero, and the installer treats that as
fatal (upstream issue #94). Until a fixed `echoctl` is released and pinned, the add-on creates
a RAM-only placeholder at `/system/vendor/etc/init/echolocal-placeholder.rc` in TWRP before
invoking `echoctl`. **Remove this workaround when the fixed release is pinned** (see
`upstream-initrc-fix.md`).

## D5 — Do not fork upstream (2026-10-09)

The bug is a one-line fix upstream. Forking `echoctl` would mean carrying a divergent binary
and losing upstream fixes. Instead the fix is proposed upstream (patch + issue #94 comment in
`upstream-initrc-fix.md`) and, in the meantime, the add-on works around it.

## D6 — `alpine` + `android-tools` + stdlib Python (2026-10-09)

The image is plain `alpine:3.21` with `python3` and `android-tools` (which ships `/usr/bin/adb`)
rather than the s6-based Home Assistant base image. The server is Python's stdlib only, so there
is no `pip` step and nothing to keep patched. `android-tools` was verified to provide `adb` on
Alpine 3.21.

## D7 — Button-mode map verified against the XDA guide (2026-10-09)

Verified from the amonet-biscuit XDA guide (Rortiz2, v2.0.0,
https://xdaforums.com/t/unlock-root-twrp-unbrick-amazon-echo-dot-2nd-gen-2016-biscuit.4761416/):

- Unlock entry (healthy Dot, **no disassembly**): unplug power, hold the **action button**,
  plug power in → **green** LED = Amazon factory fastboot → run `fastbrick` from a PC.
  Test-point shorting is only the Option 2 route for a fully bricked unit.
- After unlock, the volume buttons switch boot modes: **Volume Up = TWRP** (steady white LED),
  **Volume Down = hacked fastboot** (rainbow), **Mute = USBDL/preloader** (no LED, unbrick only).

Consequences: entering TWRP for an install is always a manual Volume-Up hold; hold Mute and the
device goes to USBDL, not recovery. The earlier "hold mute or volume-up" phrasing in this
README/session was wrong and superseded by this note. The add-on runs neither the unlock nor
the TWRP entry.

## D8 — The EchoMuse clean is file-level, never a partition (2026-10-18)

Converting a Dot away from EchoMuse leaves a file footprint on `/data` that `echoctl install`
does not remove: `/data/emos`, the EchoMuse firmware in `/data/local/bin`, Magisk in
`/data/adb`, and stale Android Wi-Fi state in `/data/misc/wifi`. The add-on's optional
**Clean previous install leftovers** checkbox (added for exactly this case) removes those
paths over `adb` in TWRP before the flash.

It deliberately does **not** wipe any partition. The biscuit's "unneeded" partitions are a
trap: the amonet payload (`boot_a_amonet`/`boot_b_amonet`), LK, `nvram`/`proinfo` and the
second boot slot are each either a brick, a lost unlock, lost radio calibration, or the
device's last-resort recovery image. Partition numbering also differs between amonet v1.1.0
and v2.0.0, so any partition-level action would have to resolve by name and carry real risk
for little gain — the leftovers that actually matter live in files. A broader clean (cache,
full userdata format, wiping slot B) can be added later, opt-in, if a real need shows up.

## D9 — Bump to echoctl 0.0.9, drop the #94 workaround (2026-10-18)

Upstream fixed the `initRC` glob bug (ygelfand/echolocal#94) — the `ls` non-zero-exit-when-a-
glob-misses problem plus the dangling `/system_root/vendor` symlink — in the `0.0.9` release
(2026-10-15; the `system.go` change landed 2026-10-08). Verified directly: the `0.0.9` tag's
`initRC` uses `ShellCode` and resolves the vendor path via `readlink`/`vendorUnder`, matching
`main`. So D4's RAM-placeholder workaround and `apply_vendor_workaround` are removed and
`echoctl_version` moves off 0.0.8. D3's intent (pin a tested version, bump deliberately when a
fix ships) still holds — and this bump should be confirmed on a real Dot before it is relied on,
since all prior field evidence was gathered on 0.0.8.

## D10 — Follow upstream releases by default (2026-10-18)

D3 pinned `echoctl` to a tested version, which meant the add-on silently went stale (0.0.9
shipped the #94 fix while we stayed on 0.0.8 and nobody noticed). At the maintainer's direction
the default now *follows* the newest stable upstream release (`echoctl_version: latest`),
resolved via GitHub's `/releases/latest` (excludes prereleases/drafts) and cached for an hour.
An explicit tag still pins or rolls back for safety, checksums are still verified against
`checksums.txt`, and a known-good fallback tag is used if GitHub is unreachable. This
supersedes D3's pin-by-default stance; the escape hatch keeps the tested-version safety net
available when it matters.
