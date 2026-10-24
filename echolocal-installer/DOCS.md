# EchoLocal Installer

An add-on that flashes and installs [EchoLocal](https://github.com/ygelfand/echolocal) onto an
unlocked 2nd-generation Amazon Echo Dot, over USB, from a Home Assistant sidebar panel.

## Prerequisites

The add-on **cannot unlock** a device and **cannot boot it into recovery**. The Dot must already
be:

- unlocked with the amonet-biscuit procedure (TWRP as recovery) — a **one-time** PC step with
  **no disassembly**: unplug power, hold the **action button** ("•"), plug back in → green LED,
  run `fastbrick`, type `YES`. **Nothing else from the unlock article is needed** — no FireOS
  re-flash, no root. See the [XDA guide](https://xdaforums.com/t/unlock-root-twrp-unbrick-amazon-echo-dot-2nd-gen-2016-biscuit.4761416/), **and**
- booted into **TWRP recovery** — hold **ONLY the Volume Up button** and apply power, keeping
  it held until the LED is **steady white** (Volume Down = hacked fastboot, Mute = USBDL — not
  TWRP), **and**
- connected to this Home Assistant host with a USB cable that carries data.

## Configuration

| Option | Default | Description |
| --- | --- | --- |
| `echoctl_version` | `latest` | Which upstream `echoctl` to download. `latest` (the default) follows the newest **stable** [ygelfand/echolocal](https://github.com/ygelfand/echolocal) release automatically (prereleases/drafts excluded), so the add-on never goes stale. Set an explicit tag (e.g. `0.0.9`) to pin or roll back. Checksums are always verified; a known-good fallback is used if GitHub is unreachable. |

The add-on downloads the pinned `echoctl` Linux build for the host architecture at first use and
verifies its SHA-256 against the release's `checksums.txt`. The binary and adb keys persist in
`/data` so a rebuild does not invalidate device trust.

## Using it

1. Boot the Dot into TWRP recovery (hold **Volume Up**, apply power, steady white LED), then
   **move it to this host**: unplug it and plug into the Home Assistant host's USB **while
   holding Volume Up** so it powers up back into TWRP, and open the **EchoLocal Installer**
   panel.
2. Press **Refresh** and pick the device. It should list with state `recovery`.
3. Enter a name and your Wi-Fi details, then press **Install**.
4. Watch the log. When it finishes, the panel shows the **pairing (encryption) key** if one
   was generated, or notes zero-PSK provisioning if not.
5. **Pair it in Home Assistant.** Copy the key, then open **Settings → Devices & Services →
   ESPHome** — the new Dot appears as a discovered device. Press **Configure** on it (or
   **Add Device** and enter the Dot's IP address) and **paste the encryption key** into the
   config flow; the device and its entities are then created. With zero-PSK provisioning
   there is no key to paste — choose the zero-PSK / push-key option in the flow instead.

## Notes

- **Installer only.** The add-on does not change Wi-Fi afterwards, reinstall, uninstall, or add
  any entities.
- **Optional leftover cleanup.** Tick **Clean previous install leftovers** on the install form
  to remove a previous EchoMuse/Magisk footprint from `/data` (`/data/emos`, `/data/local/bin`,
  `/data/adb`, `/data/misc/wifi`) before the flash. It is file-level only and never writes a
  partition, so the bootloader, the amonet unlock, TWRP and the radio calibration are
  untouched. Leave it unticked for a fresh or already-clean Dot; anything not present is
  skipped.
- **The install log is saved.** Every run is written to `/data/last-install.log`, rewritten at
  the start of each install so it always holds the most recent run, and served read-only at
  `api/last-log` on the panel origin. Startup/download lines are not written, and the file
  carries the same redacted content as the panel log.

## Troubleshooting

- **No device detected** — confirm TWRP recovery and a data-capable cable. For some hosts,
  enable **Protection mode off** and set the add-on option `full_access: true` instead of
  relying on `usb: true`.
- **Install stops at `selinux permissive` or `device name`** — reboot the Dot fresh into TWRP
  and run Install again; check `/data/last-install.log` for where it stopped.
- **Wi-Fi fails** — for a secured network the passphrase is required; a blank one joins with an
  empty password. A blank SSID only works when the Dot is already connected to a network.

## Support

The underlying tool is upstream: [ygelfand/echolocal](https://github.com/ygelfand/echolocal).
Issues about this installer belong in
[this repository](https://github.com/MJP-76/hass-apps/issues).