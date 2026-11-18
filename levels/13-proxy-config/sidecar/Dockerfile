# 企业里那种"唯一出口"的正向代理（HTTP/HTTPS CONNECT 都能走）
FROM --platform=$TARGETPLATFORM ubuntu:22.04

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
 && apt-get install -y --no-install-recommends tinyproxy ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN sed -i 's/^Listen 127.0.0.1/Listen 0.0.0.0/' /etc/tinyproxy/tinyproxy.conf \
 && sed -i 's/^Allow 127.0.0.1/Allow 0.0.0.0\/0/' /etc/tinyproxy/tinyproxy.conf \
 && grep -E '^(Port|Listen|Allow)' /etc/tinyproxy/tinyproxy.conf

EXPOSE 8888
CMD ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
