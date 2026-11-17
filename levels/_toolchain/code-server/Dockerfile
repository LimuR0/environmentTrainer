# 共享的 code-server 层：所有需要内嵌编辑器的关卡都从这里 COPY，
# 保证 233MB 的编辑器只存一份。
FROM --platform=$TARGETPLATFORM debian:12-slim

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
