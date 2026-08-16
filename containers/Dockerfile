# ==============================================================================
# RakshakX Sandbox Environment
# Multi-stage Docker build for autonomous offensive security execution
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Go Builder - Build static Go security binaries
# ------------------------------------------------------------------------------
FROM kalilinux/kali-rolling:latest AS gobuilder

RUN apt-get update && \
    apt-get install -y kali-archive-keyring && \
    apt-get update && \
    apt-get install -y --no-install-recommends golang-go git ca-certificates

ENV GOBIN=/out/bin
RUN mkdir -p /out/bin && \
    go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install -v github.com/projectdiscovery/katana/cmd/katana@latest && \
    go install -v github.com/projectdiscovery/cvemap/cmd/vulnx@latest && \
    go install -v github.com/jaeles-project/gospider@latest && \
    go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest && \
    go install -v golang.org/x/vuln/cmd/govulncheck@latest

# ------------------------------------------------------------------------------
# Stage 2: Runtime Environment - Kali Linux with Pentest & Proxy Stack
# ------------------------------------------------------------------------------
FROM kalilinux/kali-rolling:latest

LABEL maintainer="RakshakX Core Team"
LABEL description="Isolated AI Pentesting Sandbox with Caido Proxy and Dynamic Exploit Toolchain"

# Update package repos and install system base
RUN apt-get update && \
    apt-get install -y kali-archive-keyring sudo && \
    apt-get update && \
    apt-get upgrade -y

# Setup unprivileged pentester user with passwordless sudo
RUN useradd -m -s /bin/bash pentester && \
    usermod -aG sudo pentester && \
    echo "pentester ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    touch /home/pentester/.hushlogin

# Create application & tool directories
RUN mkdir -p /home/pentester/tools /app/certs /workspace && \
    chown -R pentester:pentester /app/certs /home/pentester/tools /workspace

# Install CLI security tools, compilers, and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget curl git vim nano unzip tar \
    apt-transport-https ca-certificates gnupg lsb-release \
    software-properties-common \
    gcc libc6-dev \
    python3 python3-pip python3-venv python3-setuptools \
    net-tools dnsutils whois \
    file xxd \
    jq parallel ripgrep grep \
    less procps htop \
    iproute2 iputils-ping netcat-traditional \
    nmap ncat ndiff \
    sqlmap nuclei subfinder naabu ffuf \
    nodejs npm pipx \
    golang-go \
    libcap2-bin \
    gdb \
    libnss3-tools \
    chromium fonts-liberation

# Allow nmap raw socket capture without root
RUN setcap cap_net_raw,cap_net_admin,cap_net_bind_service+eip $(which nmap)

# Generate private Root CA for transparent HTTPS interception
USER pentester
RUN openssl ecparam -name prime256v1 -genkey -noout -out /app/certs/ca.key && \
    openssl req -x509 -new -key /app/certs/ca.key \
    -out /app/certs/ca.crt \
    -days 3650 \
    -subj "/C=US/ST=CA/O=Security Testing/CN=RakshakX Interception Root CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign" && \
    openssl pkcs12 -export \
    -out /app/certs/ca.p12 \
    -inkey /app/certs/ca.key \
    -in /app/certs/ca.crt \
    -passout pass:"" \
    -name "RakshakX Root CA" && \
    chmod 644 /app/certs/ca.crt && \
    chmod 600 /app/certs/ca.key && \
    chmod 600 /app/certs/ca.p12

# Install CA cert to system-wide certificate trust store
USER root
RUN cp /app/certs/ca.crt /usr/local/share/ca-certificates/rakshakx-ca.crt && \
    update-ca-certificates

# Install modern uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh

USER pentester
WORKDIR /tmp

# Copy static Go binaries from stage 1
COPY --from=gobuilder --chown=pentester:pentester /out/bin/ /home/pentester/go/bin/

# Update nuclei vulnerability templates
RUN nuclei -update-templates || true

# Python CLI security tools via pipx
RUN pipx install arjun && \
    pipx install dirsearch && \
    pipx inject dirsearch 'setuptools<81' && \
    pipx install wafw00f && \
    pipx install semgrep && \
    pipx install bandit

# Global Node.js tools & AST tools
ENV NPM_CONFIG_PREFIX=/home/pentester/.npm-global
RUN mkdir -p /home/pentester/.npm-global && \
    npm install -g retire@latest && \
    npm install -g eslint@latest && \
    npm install -g js-beautify@latest && \
    npm install -g @ast-grep/cli@latest && \
    npm install -g tree-sitter-cli@latest && \
    npm install -g agent-browser@0.26.0 && \
    npm cache clean --force && \
    ln -sf ast-grep /home/pentester/.npm-global/lib/node_modules/@ast-grep/cli/sg

# Configure agent-browser headless Chromium defaults
ENV AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium
ENV AGENT_BROWSER_USER_AGENT="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
ENV AGENT_BROWSER_ARGS="--disable-blink-features=AutomationControlled,--no-first-run,--no-default-browser-check,--lang=en-US"
ENV AGENT_BROWSER_SCREENSHOT_DIR=/workspace/.agent-browser-screenshots
ENV AGENT_BROWSER_IDLE_TIMEOUT_MS=180000

USER root
RUN set -eu; \
    { \
        for var in AGENT_BROWSER_EXECUTABLE_PATH AGENT_BROWSER_USER_AGENT \
                   AGENT_BROWSER_ARGS AGENT_BROWSER_SCREENSHOT_DIR \
                   AGENT_BROWSER_IDLE_TIMEOUT_MS; do \
            eval "value=\${$var}"; \
            printf 'export %s="${%s:-%s}"\n' "$var" "$var" "$value"; \
        done; \
    } > /tmp/agent-browser.sh && \
    install -m 0644 /tmp/agent-browser.sh /etc/profile.d/agent-browser.sh && \
    rm /tmp/agent-browser.sh

# Tree-sitter multi-language grammar setup
USER pentester
RUN set -eux; \
    TS_PARSER_DIR="/home/pentester/.tree-sitter/parsers"; \
    mkdir -p "${TS_PARSER_DIR}"; \
    for repo in tree-sitter-java tree-sitter-javascript tree-sitter-python tree-sitter-go tree-sitter-bash tree-sitter-json tree-sitter-yaml tree-sitter-typescript; do \
        if [ "$repo" = "tree-sitter-yaml" ]; then \
            repo_url="https://github.com/tree-sitter-grammars/${repo}.git"; \
        else \
            repo_url="https://github.com/tree-sitter/${repo}.git"; \
        fi; \
        if [ ! -d "${TS_PARSER_DIR}/${repo}" ]; then \
            git clone --depth 1 "${repo_url}" "${TS_PARSER_DIR}/${repo}"; \
        fi; \
    done; \
    if [ -d "${TS_PARSER_DIR}/tree-sitter-typescript/typescript" ]; then \
        ln -sfn "${TS_PARSER_DIR}/tree-sitter-typescript/typescript" "${TS_PARSER_DIR}/tree-sitter-typescript-typescript"; \
    fi; \
    if [ -d "${TS_PARSER_DIR}/tree-sitter-typescript/tsx" ]; then \
        ln -sfn "${TS_PARSER_DIR}/tree-sitter-typescript/tsx" "${TS_PARSER_DIR}/tree-sitter-typescript-tsx"; \
    fi; \
    tree-sitter init-config >/dev/null 2>&1 || true; \
    TS_CONFIG="/home/pentester/.config/tree-sitter/config.json"; \
    mkdir -p "$(dirname "${TS_CONFIG}")"; \
    [ -f "${TS_CONFIG}" ] || printf '{}\n' > "${TS_CONFIG}"; \
    TMP_CFG="$(mktemp)"; \
    jq --arg p "${TS_PARSER_DIR}" '.["parser-directories"] = ((.["parser-directories"] // []) + [$p] | unique)' "${TS_CONFIG}" > "${TMP_CFG}"; \
    mv "${TMP_CFG}" "${TS_CONFIG}"

WORKDIR /home/pentester/tools
RUN git clone https://github.com/ticarpi/jwt_tool.git && \
    chmod +x jwt_tool/jwt_tool.py

# Secret scanners & Trivy
USER root
ARG TRUFFLEHOG_VERSION=3.95.9
RUN curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /home/pentester/.local/bin "v${TRUFFLEHOG_VERSION}" && \
    chown -R pentester:pentester /home/pentester/.local

RUN set -eux; \
    ARCH="$(uname -m)"; \
    case "$ARCH" in \
        x86_64) GITLEAKS_ARCH="x64" ;; \
        aarch64|arm64) GITLEAKS_ARCH="arm64" ;; \
        *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;; \
    esac; \
    TAG="$(curl -fsSL https://api.github.com/repos/gitleaks/gitleaks/releases/latest | jq -r .tag_name)"; \
    curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/${TAG}/gitleaks_${TAG#v}_linux_${GITLEAKS_ARCH}.tar.gz" -o /tmp/gitleaks.tgz; \
    tar -xzf /tmp/gitleaks.tgz -C /tmp; \
    install -m 0755 /tmp/gitleaks /usr/local/bin/gitleaks; \
    rm -f /tmp/gitleaks /tmp/gitleaks.tgz

RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Install Caido CLI proxy daemon
ARG CAIDO_VERSION=0.56.0
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        CAIDO_ARCH="x86_64"; \
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        CAIDO_ARCH="aarch64"; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    wget -O caido-cli.tar.gz "https://caido.download/releases/v${CAIDO_VERSION}/caido-cli-v${CAIDO_VERSION}-linux-${CAIDO_ARCH}.tar.gz" && \
    tar -xzf caido-cli.tar.gz && \
    chmod +x caido-cli && \
    rm caido-cli.tar.gz && \
    mv caido-cli /usr/local/bin/

# Set environment PATH across all subshells
ENV PATH="/home/pentester/go/bin:/home/pentester/.local/bin:/home/pentester/.npm-global/bin:/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Setup Python Sandbox venv
USER pentester
WORKDIR /app
RUN python3 -m venv /app/.venv && \
    /app/.venv/bin/pip install --no-cache-dir caido-sdk-client && \
    /app/.venv/bin/pip install --no-cache-dir \
        requests httpx beautifulsoup4 lxml pyjwt cryptography && \
    /app/.venv/bin/pip install --no-cache-dir -r /home/pentester/tools/jwt_tool/requirements.txt && \
    printf '%s\n' \
        '#!/bin/bash' \
        'exec /app/.venv/bin/python /home/pentester/tools/jwt_tool/jwt_tool.py "$@"' \
        > /home/pentester/.local/bin/jwt_tool && \
    chmod +x /home/pentester/.local/bin/jwt_tool

RUN echo 'export PATH="/home/pentester/go/bin:/home/pentester/.local/bin:/home/pentester/.npm-global/bin:/app/.venv/bin:$PATH"' >> /home/pentester/.bashrc && \
    echo 'export PATH="/home/pentester/go/bin:/home/pentester/.local/bin:/home/pentester/.npm-global/bin:/app/.venv/bin:$PATH"' >> /home/pentester/.profile

# Clean up apt caches to minimize image footprint
USER root
RUN apt-get autoremove -y && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy Entrypoint
COPY containers/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER pentester
WORKDIR /workspace

ENTRYPOINT ["docker-entrypoint.sh"]
