FROM --platform=$TARGETPLATFORM debian:12-slim

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

# 先正常装工具，并把 cowsay 的 deb 预下载到 /opt/debs（断网兜底）
# 先把 cowsay 的依赖装齐（避免运行时仓库版本漂移导致依赖冲突），
# 再把 cowsay 本身卸掉、留下离线 deb —— 学员只需装这一个包
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      vim-tiny nano less procps ca-certificates cowsay \
 && mkdir -p /opt/debs \
 && apt-get install -y --download-only --reinstall cowsay \
 && cp -a /var/cache/apt/archives/cowsay*.deb /opt/debs/ \
 && apt-get remove -y cowsay \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && ls /opt/debs

# 手写源文件时最常见的错：只写了地址和代号，漏了组件（main）：
#   deb http://deb.debian.org/debian bookworm      <- 少一个 main
# 同时删掉 Debian 12 默认的 deb822 源，让错误只暴露在这一处
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && printf 'deb http://deb.debian.org/debian bookworm\n' > /etc/apt/sources.list \
 && cat /etc/apt/sources.list

WORKDIR /work
COPY task/ /work/
COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;31m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 11 关 · apt 源写错
  ------------------------------------------------------------
  系统     : Debian 12 (bookworm)
  症状     : apt-get update 报 Malformed entry（少写了 main 组件）
  离线兜底 : /opt/debs 里有 cowsay 的 deb
  目标     : cowsay 能正常输出

EOF

CMD ["sleep", "infinity"]
