FROM --platform=$TARGETPLATFORM ubuntu:22.04

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
 && apt-get install -y --no-install-recommends \
      git vim-tiny nano less procps ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY task/ /work/app/
COPY setup-repo.sh /opt/setup-repo.sh
RUN chmod +x /opt/setup-repo.sh && /opt/setup-repo.sh && rm /opt/setup-repo.sh

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'BASHRC'
export PS1='\[\e[0;32m\][sandbox /work/app]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
alias gs='git status -sb'
alias gl='git log --oneline --graph --all'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
BASHRC

RUN cat > /etc/motd <<'MOTD'

  第 14 关 · Git：把两个分支合干净
  ------------------------------------------------------------
  仓库     : /work/app
  现状     : feature/login 等着合并，main 上改了同样的文件（会冲突）
             有人把 node_modules 提交进去了
             提交身份还没配
  目标     : 合并完成、冲突解干净、node_modules 不再被跟踪、工作区干净

MOTD

# 内嵌编辑器（冲突解决用编辑器比 vim 顺手）
COPY --from=envtrainer/toolchain:code-server /opt/code-server /opt/code-server
RUN ln -sf /opt/code-server/bin/code-server /usr/local/bin/code-server

WORKDIR /work/app
CMD ["sleep", "infinity"]
