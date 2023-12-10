#!/bin/sh
# shellcheck source=/dev/null

if [ -z "${FAIL2BAN_SOCAT_HOST}" ] && [ -z "${FAIL2BAN_SOCAT_FILE}" ]; then
	true
else
	echo "Socat : ${FAIL2BAN_SOCAT_FILE} -> ${FAIL2BAN_SOCAT_HOST}"
	socat UNIX-LISTEN:"${FAIL2BAN_SOCAT_FILE}",fork TCP:"${FAIL2BAN_SOCAT_HOST}" &
fi

. "${VIRTUAL_ENV}"/bin/activate
python3 "${SCRIPT}"
