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

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      vim-tiny nano less procps ca-certificates curl file \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work

# 离线轮子缓存：机器断网时也能完成本关（单独一层，改项目代码不会触发重下）
COPY task/requirements.txt /tmp/requirements.txt
RUN mkdir -p /opt/wheels \
 && pip download -d /opt/wheels -r /tmp/requirements.txt \
 && pip download -d /opt/wheels "setuptools<70" wheel

COPY task/ /work/

# 模拟"被别的项目污染过的全局 Python 环境"（老版本 Flask + 老版本 requests）
RUN pip install --no-cache-dir \
      "flask==2.0.1" "werkzeug==2.0.3" "jinja2==3.0.3" \
      "itsdangerous==2.0.1" "click==8.0.4" "markupsafe==2.0.1" \
      "requests==2.28.1"

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[1;36m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 1 关 · Python 依赖冲突
  ------------------------------------------------------------
  工作目录 : /work          （项目文件在这里）
  全局环境 : Flask 2.0.1    （被别的项目占着，不要动它）
  目标     : 让 ./.venv/bin/python app.py --selftest 输出 SELFTEST OK
  离线轮子 : /opt/wheels    （断网时用 --no-index --find-links /opt/wheels）

EOF

# 内嵌编辑器（共享层，四个关卡共用同一份 code-server）
COPY --from=envtrainer/toolchain:code-server /opt/code-server /opt/code-server
RUN ln -sf /opt/code-server/bin/code-server /usr/local/bin/code-server

CMD ["sleep", "infinity"]
