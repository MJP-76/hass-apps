# amonet-biscuit — vendored scripts

Verbatim copies of the amonet `mt8163-biscuit` scripts we rely on (Rortiz2 / k4y0z,
[R0rt1z2/amonet](https://github.com/R0rt1z2/amonet)), kept in this repository because they are
the known-working way to unlock a Dot and to put an unlocked Dot into TWRP.

For EchoLocal, these are the only amonet scripts this project needs — the rest of the XDA
article (FireOS re-flash, A/B slot switching, boot-root) is not required.

## Contents

| File | Purpose |
| --- | --- |
| `fastbrick.sh` | **The one-time unlock.** Run on a Windows/Linux PC while the Dot is in factory fastboot (action button + power → green ring). Prompts for `YES`, flashes the exploit; the Dot reboots into TWRP (white ring). Windows users use `fastbrick.bat` from the same package (upstream provides it; we vendor the shell one). |
| `fastboot-step.sh` | **Post-unlock TWRP entry from a PC.** From hacked fastboot (Volume Down → rainbow ring): flashes `bin/twrp.img` and reboots straight into TWRP. |

## fastbrick.sh — the unlock

```sh
# from inside the extracted amonet-biscuit-*.zip release folder
./fastbrick.sh        # Linux   (Windows: double-click fastbrick.bat)
# type YES when prompted; DO NOT interrupt after the 10-second grace period
```

`fastbrick.sh` needs the package around it (`profile.sh`, `bin/` payloads, the python `modules/`),
so run the **full extracted package** and use this copy as the known-good reference — or run it
from `/path/to/amonet-biscuit-2.0.0/` with this file dropped alongside.

## fastboot-step.sh — enter TWRP from a PC (already-unlocked Dot)

```sh
# from inside the extracted release folder (bin/fastboot + bin/twrp.img present)
./fastboot-step.sh
```

## How to run either from this repository

Neither is self-contained: each needs the images/binaries from the upstream release package.
Drop the file into your extracted `amonet-biscuit-*.zip` folder and run it there.

## Provenance

- Upstream:
  - https://github.com/R0rt1z2/amonet/blob/mt8163-biscuit/fastbrick.sh
  - https://github.com/R0rt1z2/amonet/blob/mt8163-biscuit/fastboot-step.sh
- Vendored at pin: copied from the `mt8163-biscuit` branch, October 2026.
- SHA-256 (verified on vendor):

```text
fastbrick.sh     d7a025ed7e1567aaf01d67803f5bad9eed0942e92935f253ecfba1a7dd02d723
fastboot-step.sh f529e48a20af265e96a6dbac5d7a6d4ad8e112785ee720b99f1624ebe5c2bd0c
```

- License: upstream repository is MIT / GPL-2.0 overall. See the upstream LICENSE files.