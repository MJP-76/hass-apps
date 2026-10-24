ARG BUILD_VERSION
ARG BUILD_ARCH

FROM alpine:3.21

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

# android-tools ships /usr/bin/adb and /usr/bin/fastboot on Alpine.
RUN apk add --no-cache \
      python3 \
      android-tools \
      curl \
      ca-certificates \
      tzdata

COPY run.sh /run.sh
COPY app /app

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]