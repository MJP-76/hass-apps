#!/bin/sh
# Tuya IPC Terminal add-on entrypoint.
#
# Keeps its session under /data/.tuya-data so authentication survives add-on
# restarts and updates. Authentication is done once, either from the password
# option (email/password login) or by importing a session (see the README).

set -e

BIN=/bin/tuya-ipc-terminal
OPTIONS=/data/options.json

region=$(jq -r '.region // "eu-central"' "${OPTIONS}")
email=$(jq -r '.email // ""' "${OPTIONS}")
password=$(jq -r '.password // ""' "${OPTIONS}")
port=$(jq -r '.port // 8554' "${OPTIONS}")
resolution=$(jq -r '.resolution // "hd"' "${OPTIONS}")

cd /data

has_session() {
    ls /data/.tuya-data/user_*.json >/dev/null 2>&1
}

if ! has_session; then
    if [ -z "${email}" ] || [ -z "${password}" ]; then
        echo "ERROR: No Tuya session found and no credentials configured."
        echo "Set 'email' and 'password' in the add-on configuration, or import"
        echo "an existing session into /data/.tuya-data (see the add-on README)."
        exit 1
    fi
    echo "No session found - authenticating ${email} in ${region}..."
    # The password is piped; our password-non-tty patch makes the tool read
    # it as a plain line outside a terminal. Pipes are never echoed, so the
    # password cannot end up in the logs.
    printf '%s\n' "${password}" | "${BIN}" auth add "${region}" "${email}" --password
fi

echo "Authenticated users:"
"${BIN}" auth list || true

echo "Refreshing camera discovery..."
"${BIN}" cameras refresh || echo "Camera discovery failed - continuing with cached list."

echo "Starting RTSP server on port ${port} (resolution: ${resolution})."
echo "Stream (from other add-ons): rtsp://46d52ae8-tuya-ipc-terminal:${port}/<Camera_Name>"
echo "Stream (from your LAN): rtsp://<home-assistant>:<host-port-from-network-panel>/<Camera_Name>"
exec "${BIN}" rtsp start --port "${port}"
