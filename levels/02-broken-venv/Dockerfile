FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      vim-tiny nano less procps ca-certificates file \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY task/ /work/

# 离线轮子
RUN mkdir -p /opt/wheels && pip download -d /opt/wheels "click==8.1.7" || true

# 先在 /tmp/tool 建好 venv（shebang 写成 /tmp/tool/bin/python），再整体搬到 /work/tool
# 模拟"把虚拟环境直接拷贝到别的机器/别的路径"这个经典事故
RUN python -m venv /tmp/tool \
 && /tmp/tool/bin/pip install --no-index --find-links /opt/wheels "click==8.1.7" \
 && cp -a /tmp/tool /work/tool \
 && rm -rf /tmp/tool \
 && find /work/tool -name '__pycache__' -type d -prune -exec rm -rf {} +

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[1;35m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
cat /etc/motd 2>/dev/null
EOF
RUN cat > /etc/motd <<'EOF'

  第 2 关 · 搬家搬坏的虚拟环境
  ------------------------------------------------------------
  工作目录 : /work            里面有 tool/ 这个虚拟环境
  症状     : ./tool/bin/python 能跑，./tool/bin/pip 报 bad interpreter
  目标     : 让 tool 在 /work/tool 下自洽可用
  离线轮子 : /opt/wheels

EOF

CMD ["sleep", "infinity"]
