FROM --platform=$TARGETPLATFORM maven:3.9-eclipse-temurin-17

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
