FROM --platform=$TARGETPLATFORM node:20-bookworm-slim

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

# 第二个 node：apt 源里的 18.x，落在 /usr/bin/node
RUN apt-get update \
 && apt-get install -y --no-install-recommends nodejs vim-tiny nano less procps ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# 手动装的那份 node 20（镜像自带，在 /usr/local/bin），收进 /opt/node20/bin
RUN mkdir -p /opt/node20/bin \
 && ln -sf /usr/local/bin/node /opt/node20/bin/node \
 && ln -sf /usr/local/bin/npm /opt/node20/bin/npm \
 && ln -sf /usr/local/lib/node_modules /opt/node20/lib

# 关键：PATH 里没有 /usr/local/bin，所以裸敲 node 命中的是 /usr/bin/node（18）
ENV PATH=/usr/sbin:/usr/bin:/sbin:/bin
ENV HOME=/root

# node 官方镜像的 entrypoint 在 /usr/local/bin，PATH 里已经没有它了
ENTRYPOINT []

WORKDIR /work
COPY task/ /work/
RUN chmod +x /work/run.sh

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;32m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 7 关 · 环境变量冲突（PATH）
  ------------------------------------------------------------
  工作目录 : /work
  症状     : ./run.sh 报 node: bad option: --env-file
  机器上   : /usr/bin/node (v18) 和 /opt/node20/bin/node (v20) 两个版本
  目标     : 新开的 shell 里 node -v 是 v20，./run.sh 能跑通

EOF

CMD ["sleep", "infinity"]
