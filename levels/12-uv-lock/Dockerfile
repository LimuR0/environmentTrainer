FROM --platform=$TARGETPLATFORM python:3.11-slim

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

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 \
    UV_CACHE_DIR=/opt/uv-cache \
    UV_LINK_MODE=copy

RUN apt-get update \
 && apt-get install -y --no-install-recommends vim-tiny nano less procps ca-certificates git \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv>=0.9" && uv --version

WORKDIR /work
COPY task/ /work/

# 备份「新」pyproject（含 httpx），并造一份「旧」的（不含 httpx）
RUN cp /work/pyproject.toml /tmp/pyproject.new.toml
RUN python - <<'PY'
import pathlib
s = pathlib.Path('/tmp/pyproject.new.toml').read_text()
pathlib.Path('/tmp/pyproject.old.toml').write_text(s.replace('    "httpx==0.27.2",\n', ''))
PY

# 1) 用旧清单生成旧 lock
RUN cp /tmp/pyproject.old.toml /work/pyproject.toml \
 && uv lock \
 && cp /work/uv.lock /tmp/uv.old.lock

# 2) 用新清单预热缓存（把所有包都下到 UV_CACHE_DIR，断网也能同步）
RUN cp /tmp/pyproject.new.toml /work/pyproject.toml && uv sync

# 3) 回到故障现场：新清单 + 旧 lock + 没有 .venv
RUN rm -rf /work/.venv /work/uv.lock && cp /tmp/uv.old.lock /work/uv.lock \
 && grep -c 'name = ' /work/uv.lock

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;35m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 12 关 · uv lock 过期
  ------------------------------------------------------------
  工作目录 : /work
  症状     : uv sync --frozen 报 lock 需要更新
  缓存     : UV_CACHE_DIR 已预热（断网也能同步）
  目标     : uv lock --check 通过 + uv run pytest 通过

EOF

CMD ["sleep", "infinity"]
