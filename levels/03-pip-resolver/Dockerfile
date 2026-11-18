FROM python:3.11-slim

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

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends vim-tiny nano less procps curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# 离线轮子：两条可行路线都备好（pip download 不能直接按冲突的 requirements 下载，
# 所以分两组分别解析）
RUN mkdir -p /opt/wheels \
 && pip download -q -d /opt/wheels "fastapi==0.95.0" "httpx==0.27.2" \
 && pip download -q -d /opt/wheels "fastapi==0.115.5" "pydantic==2.5.3" "httpx==0.27.2" \
 && ls /opt/wheels | wc -l

COPY task/ /work/
COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;33m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 3 关 · 依赖解析死锁
  ------------------------------------------------------------
  工作目录 : /work
  症状     : pip install -r requirements.txt 直接报 ResolutionImpossible
  代码要求 : app.py 用了 pydantic v2 的 model_dump()
  目标     : 修正依赖，让 ./.venv/bin/python app.py --selftest 输出 SELFTEST OK
  离线轮子 : /opt/wheels

EOF

CMD ["sleep", "infinity"]
