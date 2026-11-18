FROM --platform=$TARGETPLATFORM golang:1.22-bookworm

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
 && apt-get install -y --no-install-recommends vim-tiny nano less procps ca-certificates git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY task/ /work/

# 先把模块缓存准备好（离线可用）
RUN GOFLAGS=-mod=mod go mod tidy \
 && GOFLAGS=-mod=mod go mod download \
 && ls $(go env GOMODCACHE)/github.com/google

# 制造现场：有人手动往 go.mod 加了依赖，却没有同步 go.sum
# （等价于 git 里只提交了 go.mod，忘了 go.sum）
RUN rm -f go.sum && rm -rf vendor

# CI 是离线的，模块只能用本地缓存
ENV GOPROXY=off

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;36m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 9 关 · Go modules / vendor 不一致
  ------------------------------------------------------------
  工作目录 : /work
  当前配置 : GOPROXY=off（离线，只能用本地模块缓存）
  症状     : go build 报 missing go.sum entry
  模块缓存 : 已经预热（$GOMODCACHE）
  目标     : go test ./... 通过

EOF

# 内嵌编辑器（共享层，四个关卡共用同一份 code-server）
COPY --from=envtrainer/toolchain:code-server /opt/code-server /opt/code-server
RUN ln -sf /opt/code-server/bin/code-server /usr/local/bin/code-server

CMD ["sleep", "infinity"]
