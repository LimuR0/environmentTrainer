FROM --platform=$TARGETPLATFORM ubuntu:24.04

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

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential binutils file vim-tiny nano less procps ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# 把 g++-14 及其依赖全部离线预下载，断网也能装
RUN apt-get update \
 && apt-get install -y --download-only --no-install-recommends g++-14 \
 && mkdir -p /opt/debs \
 && cp -a /var/cache/apt/archives/*.deb /opt/debs/ \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && ls /opt/debs | head -5

WORKDIR /work
COPY task/ /work/
COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;35m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 6 关 · 编译器冲突
  ------------------------------------------------------------
  工作目录 : /work          （C++23 项目）
  本机 g++ : 13（不支持 <print>）
  离线包   : /opt/debs      （里面有 g++-14 全套 deb）
  目标     : ./build/app 输出 COMPUTE OK 4.00

EOF

CMD ["sleep", "infinity"]
