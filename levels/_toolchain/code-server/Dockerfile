# 共享的 code-server 层：所有需要内嵌编辑器的关卡都从这里 COPY，
# 保证 233MB 的编辑器只存一份。
FROM --platform=$TARGETPLATFORM debian:12-slim

# ---- mirror ---- 构建时用 --build-arg 注入镜像源（不传就用官方源）
ARG APT_MIRROR=
ARG PIP_INDEX_URL=
ARG NPM_REGISTRY=
ARG GO_MIRROR=
ENV GOPROXY=${GO_MIRROR:-https://proxy.golang.org,direct}
RUN set -e; \
    if [ -n "$APT_MIRROR" ]; then \
      APTM="$APT_MIRROR"; \
      if [ ! -f /etc/ssl/certs/ca-certificates.crt ]; then APTM=$(printf '%s' "$APT_MIRROR" | sed 's|^https://|http://|'); fi; \
      for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do \
        [ -f "$f" ] || continue; \
        sed -i "s|http://deb.debian.org|$APTM|g; s|http://archive.ubuntu.com|$APTM|g; s|http://security.ubuntu.com|$APTM|g; s|http://ports.ubuntu.com/ubuntu-ports|$APTM/ubuntu-ports|g" "$f"; \
      done; \
    fi; \
    if [ -n "$PIP_INDEX_URL" ]; then \
      mkdir -p /root/.config/pip && printf '[global]\nindex-url = %s\ntimeout = 60\n' "$PIP_INDEX_URL" > /root/.config/pip/pip.conf; \
    fi; \
    if [ -n "$NPM_REGISTRY" ]; then \
      printf 'registry=%s\n' "$NPM_REGISTRY" > /root/.npmrc; \
    fi
# ---- mirror end ----

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl tar \
 && rm -rf /var/lib/apt/lists/*

ARG CS_VERSION=4.145.2

RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) cs=amd64 ;; \
      arm64) cs=arm64 ;; \
      *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/coder/code-server/releases/download/v${CS_VERSION}/code-server-${CS_VERSION}-linux-${cs}.tar.gz" \
      | tar -xz -C /opt; \
    mv "/opt/code-server-${CS_VERSION}-linux-${cs}" /opt/code-server; \
    ln -sf /opt/code-server/bin/code-server /usr/local/bin/code-server; \
    code-server --version

CMD ["sleep", "infinity"]
