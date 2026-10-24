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

# Manual cameras: escape hatch for devices discovery cannot see (for example a
# doorbell that sits outside any room in the app). Each entry is injected into
# the tool's camera registry; the stream then negotiates live per device.
manual_count=$(jq -r '.manual_cameras | length' "${OPTIONS}" 2>/dev/null || echo 0)
if [ "${manual_count}" != "0" ] && [ "${manual_count}" != "null" ]; then
    mkdir -p /data/.tuya-data
    if [ ! -f /data/.tuya-data/cameras.json ]; then
        echo '{"cameras":[],"lastUpdated":""}' > /data/.tuya-data/cameras.json
    fi
    # The tool keys cameras by the userKey it derives at login; take it from
    # the session file it stored rather than guessing the slug rules.
    user_key=$(ls /data/.tuya-data/user_*.json 2>/dev/null | head -1 | sed 's|.*/user_||; s|\.json$||')
    i=0
    while [ "${i}" -lt "${manual_count}" ]; do
        cid=$(jq -r ".manual_cameras[${i}].id" "${OPTIONS}")
        cname=$(jq -r ".manual_cameras[${i}].name" "${OPTIONS}")
        i=$((i + 1))
        if [ -z "${cid}" ] || [ "${cid}" = "null" ]; then
            continue
        fi
        exists=$(jq --arg id "${cid}" '[.cameras[] | select(.deviceId == $id)] | length' /data/.tuya-data/cameras.json)
        if [ "${exists}" = "0" ]; then
            cpath="/$(printf '%s' "${cname}" | tr ' ' '_')"
            jq --arg id "${cid}" --arg name "${cname}" --arg path "${cpath}" --arg uk "${user_key}" \
                '.cameras += [{"userKey":$uk,"deviceId":$id,"deviceName":$name,"category":"sp","rtspPath":$path,"productId":"","uuid":"","skill":""}]
                 | .lastUpdated = (now | todate)' \
                /data/.tuya-data/cameras.json > /data/.tuya-data/cameras.json.tmp
            mv /data/.tuya-data/cameras.json.tmp /data/.tuya-data/cameras.json
            echo "Manual camera added: ${name} (${cid}) -> rtsp path ${cpath}"
        fi
    done
fi

echo "Starting RTSP server on port ${port} (resolution: ${resolution})."
echo "Stream (from other add-ons): rtsp://46d52ae8-tuya-ipc-terminal:${port}/<Camera_Name>"
echo "Stream (from your LAN): rtsp://<home-assistant>:<host-port-from-network-panel>/<Camera_Name>"
exec "${BIN}" rtsp start --port "${port}"
