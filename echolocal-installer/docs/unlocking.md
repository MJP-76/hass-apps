# Getting the Dot into TWRP recovery

The EchoLocal Installer add-on needs exactly one thing from the device: the Dot sitting in
**TWRP recovery**. Everything else in the unlock article — the FireOS re-flash, the A/B slot
switching, boot-root — is **not** needed for an EchoLocal install and is not covered here.

This page has three steps: **1)** put the Dot into TWRP, **2)** move it to the Home Assistant
host, **3)** install with the add-on.

## One-time prerequisite: the unlock

TWRP exists only on an **unlocked** Dot. If yours was never unlocked, run the amonet-biscuit
`fastbrick` exploit **once**, from a PC:

- Guide / reference: [the XDA thread](https://xdaforums.com/t/unlock-root-twrp-unbrick-amazon-echo-dot-2nd-gen-2016-biscuit.4761416/).
- Unplug power, hold the **action button** (the dot, "•"), plug power back in → **green** LED
  (Amazon factory fastboot). Release.
- Run `fastbrick.sh` (Linux) or `fastbrick.bat` (Windows); a known-working copy of the shell
  script is kept in this repo —
  [`third_party/amonet-biscuit/fastbrick.sh`](../third_party/amonet-biscuit/fastbrick.sh)
  (run it from inside the extracted amonet package). **Type `YES`** when prompted, and
  watch the LEDs. **DO NOT INTERRUPT AFTER THE 10-SECOND GRACE PERIOD — ANY INTERRUPTION BRICKS
  THE DEVICE.** Wait up to 1 minute.
- The ring goes green again and the Dot **reboots into TWRP (steady white LED)**.

This is a **one-time** step — the unlock is never needed again, and no FireOS install follows
for our purposes. If your Dot is already unlocked (e.g. running EchoLocal as another unit),
skip straight to the next step.

⚠️ The unlock is the only risky part of this whole flow and carries a
**significant risk of permanently bricking** the device. Proceed entirely at your own risk.
Never modify the bootloader or critical partitions (LK, Preloader, TZ) afterwards.

## Step 1 — Put the Dot into TWRP recovery

Choose one of these two ways:

- **Without a PC — the button (easiest).** With power unplugged, hold **ONLY the Volume Up**
  button, apply power, and keep holding until the LED ring is **steady white** — release once
  recovery is up. (Volume **Down** = hacked fastboot, rainbow LED; **Mute** = USBDL/preloader —
  neither is TWRP.)
- **From a PC — amonet's `fastboot-step.sh`.** Boot the Dot into hacked fastboot (hold
  **Volume Down**, rainbow LED), then run the known-working script we keep in this repository;
  it flashes `bin/twrp.img` and reboots the Dot straight into TWRP:
  [`third_party/amonet-biscuit/fastboot-step.sh`](../third_party/amonet-biscuit/fastboot-step.sh)
  (run it from inside the extracted `amonet-biscuit-*.zip` release folder so its `bin/fastboot`
  and `bin/twrp.img` are present).

You should now see the Dot as a recovery device (`adb devices` shows `recovery`, or the panel
lists it with state `recovery`).

## Step 2 — Move it to the Home Assistant host

With the Dot still in TWRP (white LED):

1. Unplug it from wherever it is currently connected (the PC, its charger, …).
2. Plug it into the **Home Assistant host's** USB port **while holding the Volume Up button** —
   it powers up back into TWRP.
3. In Home Assistant, open the **EchoLocal Installer** panel: press **Refresh** and the Dot
   should list with state `recovery`.

> If the panel cannot see the Dot, check the USB cable carries data and see the README's
> Troubleshooting.

## Step 3 — Install with the add-on

In the panel: pick the device, give it a **name** (Home Assistant keys the device on this), and
its **Wi-Fi** details, then press **Install**. Watch the log — when it finishes, Home
Assistant discovers the Dot as an ESPHome device and pairs it with the key the panel shows.
The add-on takes over from TWRP; leave recovery mode alone during and after the flash.

Full instructions: [README](../README.md).

## Source

- Thread (the unlock, steps as written by Rortiz2): https://xdaforums.com/t/unlock-root-twrp-unbrick-amazon-echo-dot-2nd-gen-2016-biscuit.4761416/
- amonet exploit: https://github.com/R0rt1z2/amonet (branch `mt8163-biscuit`)
- Known-working script vendored here: [`third_party/amonet-biscuit/fastboot-step.sh`](../third_party/amonet-biscuit/fastboot-step.sh)