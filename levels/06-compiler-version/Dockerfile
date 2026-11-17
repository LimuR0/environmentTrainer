FROM --platform=$TARGETPLATFORM ubuntu:24.04

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
