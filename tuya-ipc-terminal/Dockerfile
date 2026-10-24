# Tuya IPC Terminal add-on.
#
# This is deliberately a thin wrapper: the upstream project is cloned at a
# pinned commit in the build stage, one small patch is applied (speaker enable
# for talkback), and the resulting binary is run in a minimal runtime image.
# No upstream code is vendored into this repository.

# --- Build stage: upstream source at a pinned commit + local patch ----------
FROM golang:1.24-alpine AS build

# Pinned upstream commit of seydx/tuya-ipc-terminal. Bump deliberately after
# reading upstream changes; see this folder's README.
ARG TUYA_IPC_REF=d65b3e9babb4829176290b4d53195d62636f00bf

RUN apk add --no-cache git
WORKDIR /src
RUN git clone https://github.com/seydx/tuya-ipc-terminal.git . \
    && git checkout "${TUYA_IPC_REF}"

COPY patches/enable-speaker.patch /tmp/enable-speaker.patch
RUN git apply /tmp/enable-speaker.patch \
    && CGO_ENABLED=0 go build -o /out/tuya-ipc-terminal .

# --- Runtime stage ---------------------------------------------------------
FROM alpine:3.20

RUN apk add --no-cache ca-certificates jq

COPY --from=build /out/tuya-ipc-terminal /bin/tuya-ipc-terminal
COPY LICENSE-UPSTREAM /licenses/tuya-ipc-terminal-LICENSE
COPY run.sh /run.sh
RUN chmod +x /run.sh

WORKDIR /data
ENTRYPOINT ["/run.sh"]
