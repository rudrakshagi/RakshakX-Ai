#!/bin/bash
set -e

# ------------------------------------------------------------------------------
# 1. Host UID/GID Remapping (for Linux bind-mount permission harmony)
# ------------------------------------------------------------------------------
HOST_UID="${RAKSHAK_HOST_UID:-${STRIX_HOST_UID:-}}"
HOST_GID="${RAKSHAK_HOST_GID:-${STRIX_HOST_GID:-$HOST_UID}}"

if [ -n "${HOST_UID}" ] && [ "${HOST_UID}" != "0" ] && [ "${HOST_UID}" != "$(id -u)" ]; then
  exec sudo -E -- bash -c '
    set -e
    gid="${1}"
    old_uid="$2"
    old_gid="$3"
    export PATH="$4"
    shift 4
    sed -i "s|^pentester:x:${old_uid}:${old_gid}:|pentester:x:${HOST_UID}:${gid}:|" /etc/passwd
    sed -i "s|^pentester:x:${old_gid}:|pentester:x:${gid}:|" /etc/group
    chown -R "${HOST_UID}:${gid}" /home/pentester /app/certs
    chown "${HOST_UID}:${gid}" /workspace
    exec setpriv --reuid "${HOST_UID}" --regid "${gid}" --init-groups "$0" "$@"
  ' "$0" "${HOST_GID}" "$(id -u)" "$(id -g)" "$PATH" "$@"
fi

# ------------------------------------------------------------------------------
# 2. Caido Interception Proxy Bootstrap
# ------------------------------------------------------------------------------
CAIDO_PORT=48080
CAIDO_LOG="/tmp/caido_startup.log"

if [ ! -f /app/certs/ca.p12 ]; then
  echo "[RakshakX] ERROR: CA certificate file /app/certs/ca.p12 not found."
  exit 1
fi

CAIDO_UI_DOMAIN_ARGS=()
ALLOWED_DOMAINS="${RAKSHAK_CAIDO_ALLOWED_DOMAINS:-${STRIX_CAIDO_ALLOWED_DOMAINS:-}}"
if [ -n "${ALLOWED_DOMAINS}" ]; then
  IFS=',' read -ra _caido_domains <<< "${ALLOWED_DOMAINS}"
  for _d in "${_caido_domains[@]}"; do
    [ -n "$_d" ] && CAIDO_UI_DOMAIN_ARGS+=(--ui-domain "$_d")
  done
fi

echo "[RakshakX] Starting Caido interception proxy daemon on port ${CAIDO_PORT}..."
caido-cli --listen 0.0.0.0:${CAIDO_PORT} \
          --allow-guests \
          --no-logging \
          --no-open \
          "${CAIDO_UI_DOMAIN_ARGS[@]}" \
          --import-ca-cert /app/certs/ca.p12 \
          --import-ca-cert-pass "" > "$CAIDO_LOG" 2>&1 &

CAIDO_PID=$!

echo "[RakshakX] Waiting for Caido GraphQL API to initialize..."
CAIDO_READY=false
for i in {1..30}; do
  if ! kill -0 $CAIDO_PID 2>/dev/null; then
    echo "[RakshakX] ERROR: Caido process exited unexpectedly (iteration $i)."
    cat "$CAIDO_LOG" 2>/dev/null || echo "(no startup log available)"
    exit 1
  fi

  if curl -s -o /dev/null -w "%{http_code}" http://localhost:${CAIDO_PORT}/graphql/ | grep -qE "^(200|400)$"; then
    echo "[RakshakX] Caido API is ready (attempt $i)."
    CAIDO_READY=true
    break
  fi
  sleep 1
done

if [ "$CAIDO_READY" = false ]; then
  echo "[RakshakX] ERROR: Caido API failed to respond within 30 seconds."
  cat "$CAIDO_LOG" 2>/dev/null || true
  exit 1
fi

# ------------------------------------------------------------------------------
# 3. Transparent System-Wide Proxy Redirection
# ------------------------------------------------------------------------------
echo "[RakshakX] Configuring system-wide proxy environment..."

cat << EOF | sudo tee /etc/profile.d/proxy.sh
export http_proxy=http://127.0.0.1:${CAIDO_PORT}
export https_proxy=http://127.0.0.1:${CAIDO_PORT}
export HTTP_PROXY=http://127.0.0.1:${CAIDO_PORT}
export HTTPS_PROXY=http://127.0.0.1:${CAIDO_PORT}
export ALL_PROXY=http://127.0.0.1:${CAIDO_PORT}
export NO_PROXY=localhost,127.0.0.1
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
EOF

cat << EOF | sudo tee /etc/environment
http_proxy=http://127.0.0.1:${CAIDO_PORT}
https_proxy=http://127.0.0.1:${CAIDO_PORT}
HTTP_PROXY=http://127.0.0.1:${CAIDO_PORT}
HTTPS_PROXY=http://127.0.0.1:${CAIDO_PORT}
ALL_PROXY=http://127.0.0.1:${CAIDO_PORT}
NO_PROXY=localhost,127.0.0.1
EOF

. /etc/profile.d/proxy.sh || true

# ------------------------------------------------------------------------------
# 4. Inject CA into Headless Browser NSS Trust Database
# ------------------------------------------------------------------------------
echo "[RakshakX] Registering CA in Chromium trust store..."
sudo -u pentester mkdir -p /home/pentester/.pki/nssdb
sudo -u pentester certutil -N -d sql:/home/pentester/.pki/nssdb --empty-password 2>/dev/null || true
sudo -u pentester certutil -A -n "RakshakX Interception Root CA" -t "C,," -i /app/certs/ca.crt -d sql:/home/pentester/.pki/nssdb 2>/dev/null || true

mkdir -p /workspace/.agent-browser-screenshots

echo "[RakshakX] Sandbox initialization complete. Executing command..."
cd /workspace
exec "$@"
