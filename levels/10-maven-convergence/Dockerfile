FROM --platform=$TARGETPLATFORM maven:3.9-eclipse-temurin-17

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends vim-tiny nano less procps ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY task/ /work/

# 预热本地仓库，让 mvn -o 完全离线可用（enforcer / surefire / 依赖树插件都拉下来）
RUN mvn -B -q dependency:go-offline >/dev/null 2>&1 || true
RUN mvn -B -q -DskipTests package >/dev/null 2>&1 || true
RUN mvn -B -q dependency:tree >/dev/null 2>&1 || true
# 跳过 enforcer 跑一次测试，把 surefire 的 junit provider 也拉进本地仓库（否则 -o 会缺包）
RUN mvn -B -q -Denforcer.skip=true test >/dev/null 2>&1 || true
RUN rm -rf /work/target

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;33m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 10 关 · Maven 依赖收敛
  ------------------------------------------------------------
  工作目录 : /work              （Java 17 + Maven 3.9）
  症状     : mvn test 被 enforcer 的 dependencyConvergence 拦住
  本地仓库 : 已预热，建议所有命令加 -o 走离线
  目标     : mvn -o test 输出 BUILD SUCCESS

EOF

# 内嵌编辑器（共享层，四个关卡共用同一份 code-server）
COPY --from=envtrainer/toolchain:code-server /opt/code-server /opt/code-server
RUN ln -sf /opt/code-server/bin/code-server /usr/local/bin/code-server

CMD ["sleep", "infinity"]
