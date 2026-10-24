# Tuya IPC Terminal (Home Assistant add-on)

Local **RTSP bridge with two-way audio** for Tuya / Energizer Connect cameras
and doorbells — including battery video doorbells like the S16904 that expose
no ONVIF/RTSP of their own.

This add-on is a **thin wrapper** around
[`seydx/tuya-ipc-terminal`](https://github.com/seydx/tuya-ipc-terminal), which
reverse-engineers Tuya's web-client streaming APIs:

```
Doorbell ←— Tuya cloud WebRTC —→ [this add-on] ←— RTSP —→ go2rtc → Home Assistant
                                                     └→ talkback (sendonly audio track)
```

Tested against an **Energizer Connect S16904** battery video doorbell: live
H.264 video, camera audio, and confirmed talkback (the doorbell speaker plays
what is sent to the RTSP `backchannel` track).

## What is in this wrapper (and what is not)

- **Not included:** any upstream source code. The Dockerfile clones upstream at
  a **pinned commit** (`d65b3e9babb4829176290b4d53195d62636f00bf`) at build time.
- **Included:** this manifest, the `Dockerfile`, `run.sh`, one small patch, and
  the upstream MIT license (`LICENSE-UPSTREAM`, © 2025 seydx).

### The patch

`patches/enable-speaker.patch` (~20 lines): upstream advertises two-way audio
but never sends Tuya's MQTT "speaker on" (protocol 312) command, so the device
stays muted. The patch sends it once, when the first talkback packet arrives.
It is intended for upstream — once merged, this patch file should be deleted.

### Bumping the upstream pin

Change `TUYA_IPC_REF` in the `Dockerfile`, rebuild, and test both video and
talkback. Keep the patch applying cleanly (`git apply` fails loudly otherwise).

## Configuration

| Option | Default | Notes |
| --- | --- | --- |
| `region` | `eu-central` | One of `eu-central`, `eu-east`, `us-west`, `us-east`, `china`, `india` |
| `email` | *(empty)* | Your Tuya / Smart Life / Energizer Connect account email |
| `password` | *(empty)* | Account password; used **once** to create a session |
| `port` | `8554` | RTSP listen port |
| `resolution` | `hd` | `hd` (main stream) or `sd` (sub-stream) |
| `manual_cameras` | *(empty)* | Escape hatch: cameras discovery cannot see (see below) |

### Manual cameras

Discovery lists only devices that sit **inside a room** in the app. If a camera
is invisible to discovery (for example a doorbell placed directly under the
home), add it explicitly:

```yaml
manual_cameras:
  - id: bf73e7f6611ef7daa84j6b   # Tuya device ID (from the Tuya portal or logs)
    name: Back door              # becomes the RTSP path: /Back_door
```

The entry is injected into the tool's camera registry at startup; the stream is
negotiated live per device, exactly like a discovered camera.

The password is stored in the add-on's configuration by your Supervisor like
any other add-on credential. It is only read when no session exists yet.

### Authentication

On first start with `email` + `password` set, the add-on logs in and stores the
session in `/data/.tuya-data/` (persistent across restarts and updates). After
that you can clear the password from the configuration if you prefer.

Alternative (no password in the config): run `tuya-ipc-terminal auth add
<region> <email> --qr` anywhere once and copy the `.tuya-data/user_*.json` file
into the add-on's `/data/.tuya-data/`.

If the session expires (for example after Tuya terms changes), re-set the
password option and restart.

## Using the streams

The add-on serves one RTSP endpoint per camera. There are two ways to reach it:

- **From another add-on** (go2rtc, Frigate, …) over the internal network — no
  host port needed, always on container port `8554`:

  ```
  rtsp://46d52ae8-tuya-ipc-terminal:8554/<Camera_Name>
  ```

- **From your LAN** (ffplay, VLC, …) via the host port configured in the
  add-on's **Network** panel (default **8555** — `8554` is usually taken by
  go2rtc):

  ```
  rtsp://<home-assistant>:8555/<Camera_Name>
  ```

### go2rtc (recommended, enables talkback)

```yaml
streams:
  back_door:
    - rtsp://46d52ae8-tuya-ipc-terminal:8554/Back_door
```

With go2rtc in front, the Advanced Camera Card's two-way talk button sends your
browser/phone microphone into the stream's `backchannel` audio track, which
this bridge forwards to the doorbell speaker.

### Home Assistant camera entity (view only)

```yaml
camera:
  - platform: generic
    stream_source: rtsp://46d52ae8-tuya-ipc-terminal:8554/Back_door
    name: "Back door"
```

## Limitations

- **Cloud-dependent**: streams travel through Tuya's servers, like the app.
- **Awake devices only**: a battery doorbell sleeps between events; the stream
  exists while it is awake (perfect for ring-then-talk, not for 24/7 recording).
- One stream per camera is negotiated on demand; the bridge shuts idle streams
  down after a few seconds.

## Credits

- [`seydx/tuya-ipc-terminal`](https://github.com/seydx/tuya-ipc-terminal) —
  the reverse-engineered Tuya streaming bridge (MIT, © 2025 seydx).
- `go2rtc` by AlexxIT — whose WebRTC/codec utilities upstream uses.
