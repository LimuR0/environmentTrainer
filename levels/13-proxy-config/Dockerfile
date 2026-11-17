FROM --platform=$TARGETPLATFORM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv curl ca-certificates vim-tiny nano less procps iproute2 dnsutils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY task/ /work/

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'BASHRC'
export PS1='\[\e[0;31m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
BASHRC

RUN cat > /etc/motd <<'MOTD'

  第 13 关 · 代理配置
  ------------------------------------------------------------
  工作目录 : /work
  症状     : curl / pip 都连不上外网
  网络     : 这个容器没有直接出口，同网络里有一个代理服务
  目标     : 让 pip 能装包，并且代理配置活过重开 shell

MOTD

CMD ["sleep", "infinity"]
