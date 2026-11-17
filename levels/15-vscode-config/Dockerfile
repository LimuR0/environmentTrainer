FROM --platform=$TARGETPLATFORM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip git curl ca-certificates vim-tiny nano less procps \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY task/ /work/pyapp/

# 项目自带一个装好 pytest 的虚拟环境（这一关聚焦 IDE 配置，不重复讲 venv）
RUN python3 -m venv /work/pyapp/.venv \
 && /work/pyapp/.venv/bin/pip install -q --no-cache-dir -r /work/pyapp/requirements.txt \
 && /work/pyapp/.venv/bin/python -m pytest -q /work/pyapp 2>&1 | tail -2

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'BASHRC'
export PS1='\[\e[0;36m\][sandbox /work/pyapp]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
BASHRC

RUN cat > /etc/motd <<'MOTD'

  第 15 关 · VS Code 工作区配置
  ------------------------------------------------------------
  项目     : /work/pyapp（.venv 已建好，pytest 已装）
  现状     : 没有 .vscode/ 目录 —— 编辑器认不出解释器、没有调试入口、没有测试任务
  目标     : 用 .vscode/ 下的四个配置文件把这个项目"配好"

MOTD

COPY --from=envtrainer/toolchain:code-server /opt/code-server /opt/code-server
RUN ln -sf /opt/code-server/bin/code-server /usr/local/bin/code-server

WORKDIR /work/pyapp
CMD ["sleep", "infinity"]
