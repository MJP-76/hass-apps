# TODO

Single source of truth for outstanding work on this repository.

## Done

- [x] 2026-10-18 — Field-verified 0.1.6 / echoctl 0.0.9 on a real Dot (G090LF0964540CET,
      "Kitchen DOT", re-install + zero-PSK): follow-latest resolved 0.0.9, no workaround line,
      clean ran (removed /data/emos, /data/local/bin, /data/misc/wifi; /data/adb skipped),
      install 12/12 + 19/19 + 3/3, Wi-Fi up, echod resident, HA discovered it via zero-PSK.
      Retires the "confirm 0.0.9" caveat in D9. (0.0.9 logs a harmless WARN when
      /system/bin/getprop is absent — flagged upstream in ygelfand/echolocal#114.)
- [x] 2026-10-18 — Bump pinned `echoctl` to 0.0.9 and remove the TWRP `vendor/etc/init`
      workaround (`apply_vendor_workaround`): upstream fixed the `initRC` glob bug
      (ygelfand/echolocal#94) in 0.0.9. Closes the old Soon item; see decision D9.
- [x] 2026-10-18 — Field test: two EchoMuse dots (emOS flow) converted via the add-on with
      **Clean previous install leftovers** ticked. On G090LF0964540AQS ("Reception2 DOT") the
      clean removed `/data/emos`, `/data/local/bin` and `/data/misc/wifi`; `/data/adb` absent
      as expected (emOS flow installs no Magisk); post-check clean. echoctl 12/12 + 16/16 + 3/3,
      Wi-Fi up (172.16.1.115), echod resident, key handled. The vendor placeholder was not
      confirmed on this build but the install passed 'selinux permissive' anyway. The log was
      only recovered after the fact — motivated the 0.1.4 rename sync and `/data/last-install.log`.
- [x] 2026-10-09 — End-to-end test on a fresh TWRP-unlocked Dot (G090LF0964540CET, "Lounge DOT"):
      `usb: true` passthrough works on this HAOS host; add-on installed EchoLocal in ~96 s
      (root 12/12, install 16/16, Wi-Fi up, echod resident after reboot, pairing key shown).
      Required the 0.1.1 fix for install POST bodies lost through HA ingress (the ingress
      proxy sends chunked transfer encoding; the server previously read only Content-Length).

## Soon

- [ ] Add `icon.png` and `logo.png` to `echolocal_installer/`.
- [ ] Surface the post-install `echoctl status` output in the panel.

## Later

- [ ] Convenience: a "boot to recovery" button using `adb reboot recovery` for Dots already
      running rooted Android with adb authorized to this add-on — never for the first install,
      which stays a manual button combo (README, "Entering TWRP").
- [ ] Optional: re-configure Wi-Fi without a full re-install (upstream issue #83).
- [ ] Optional: expose install progress to automations (would need a companion integration).
