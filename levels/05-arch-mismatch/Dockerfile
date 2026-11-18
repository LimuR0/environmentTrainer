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
      build-essential binutils file python3 vim-tiny nano less procps ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY task/ /work/
RUN mkdir -p /work/vendor

# 造一份「与宿主架构相反」的预编译库，模拟从 release 页面下错包
ARG TARGETARCH=arm64
RUN python3 - <<'PY_ELF'
import os, struct
arch = os.environ.get("TARGETARCH", "arm64")
em = 0x3e if arch == "arm64" else 0xb7   # 与本机相反：arm64 机器放假 x86_64 库，反之亦然
e_ident = b"\x7fELF" + bytes([2, 1, 1, 0]) + b"\x00" * 8
hdr = struct.pack("<HHIQQQIHHHHHH", 3, em, 1, 0, 0, 0, 0, 64, 56, 0, 64, 0, 0)
open("/work/vendor/libmath.so", "wb").write(e_ident + hdr)
print("fake prebuilt:", arch, "-> e_machine", hex(em))
PY_ELF
RUN chmod +x /work/check.sh

COPY judge.sh /opt/judge/judge.sh
RUN chmod +x /opt/judge/judge.sh

RUN cat > /root/.bashrc <<'EOF'
export PS1='\[\e[0;36m\][sandbox /work]\[\e[0m\] \$ '
export EDITOR=vim
alias ll='ls -alF'
[ -f /tmp/.motd_shown ] || { cat /etc/motd; touch /tmp/.motd_shown; }
EOF
RUN cat > /etc/motd <<'EOF'

  第 5 关 · 架构冲突
  ------------------------------------------------------------
  工作目录 : /work
  vendor/  : release 页面上下的预编译库（架构可能不对）
  源码     : src/mathlib.c
  目标     : ./check.sh 输出 MATH OK 4.0000

EOF

CMD ["sleep", "infinity"]
