FROM --platform=$TARGETPLATFORM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends vim-tiny nano less procps ca-certificates git \
 && rm -rf /var/lib/apt/lists/*

# 把两条路线的包都灌进 npm cache，断网也能装（两个独立目录，避免互相解析冲突）
ENV npm_config_cache=/opt/npm-cache
RUN mkdir -p /tmp/warm-old && cd /tmp/warm-old \
 && npm init -y >/dev/null \
 && npm install --no-audit --no-fund --legacy-peer-deps \
      react@18.3.1 react-dom@18.3.1 @material-ui/core@4.12.4 \
 && cd / && rm -rf /tmp/warm-old

RUN mkdir -p /tmp/warm-new && cd /tmp/warm-new \
 && npm init -y >/dev/null \
 && npm install --no-audit --no-fund \
      react@18.3.1 react-dom@18.3.1 \
      @mui/material@5.15.20 @mui/icons-material@5.15.20 \
      @emotion/react@11.13.0 @emotion/styled@11.13.0 \
 && cd / && rm -rf /tmp/warm-new \
 && du -sh /opt/npm-cache

WORKDIR /work
COPY task/ /work/

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;32m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 8 关 · npm peer 依赖冲突
  ------------------------------------------------------------
  工作目录 : /work              （React 18 看板项目）
  症状     : npm install 报 ERESOLVE
  离线缓存 : npm 已配好 /opt/npm-cache（可加 --prefer-offline）
  目标     : npm ls 无冲突，npm run verify 输出 VERIFY OK

EOF

# 内嵌编辑器（共享层，四个关卡共用同一份 code-server）
COPY --from=envtrainer/toolchain:code-server /opt/code-server /opt/code-server
RUN ln -sf /opt/code-server/bin/code-server /usr/local/bin/code-server

CMD ["sleep", "infinity"]
