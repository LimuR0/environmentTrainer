#!/usr/bin/env bash
# 第 13 关判题：代理配置必须持久化（活过新 shell），并且真的能装包
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

# 1) 代理配置是否持久化（环境变量写进 shell 配置，或 pip 自己的配置）
proxy_env=$(bash -ic 'printf "%s" "${https_proxy:-$HTTPS_PROXY}${http_proxy:-$HTTP_PROXY}"' 2>/dev/null | tr -d '\r' | tail -1)
pip_proxy=$(pip3 config get global.proxy 2>/dev/null | tr -d '\r' | head -1)
[ -z "$pip_proxy" ] && pip_proxy=$(pip3 config list 2>/dev/null | grep -i proxy | head -1)

if [ -n "$proxy_env" ]; then
  ok "代理配置" "shell 里可见：$proxy_env"
elif [ -n "$pip_proxy" ]; then
  ok "代理配置" "pip 配置里可见：$pip_proxy"
else
  bad "代理配置" "新 shell 里没有 http(s)_proxy —— 只在当前终端 export 是不够的"
fi

# 2) 通过代理访问外网（在交互 shell 里跑，验证持久化配置真的生效）
code=$(bash -ic 'curl -s -o /dev/null -w "%{http_code}" --max-time 20 https://pypi.org/simple/' 2>/dev/null | tr -d '\r' | tail -1)
if [ "$code" = "200" ]; then
  ok "外网访问" "curl 走代理拿到 200"
else
  bad "外网访问" "curl 返回 ${code:-无响应}（检查 HTTPS_PROXY 是否写对）"
fi

# 3) 真的装上包
pout=$(bash -ic 'pip3 install --no-cache-dir --timeout 15 --retries 1 -q -r /work/requirements.txt' 2>&1); prc=$?
if [ $prc -eq 0 ]; then
  ok "pip 安装" "requests 装上了"
else
  bad "pip 安装" "$(echo "$pout" | grep -iE 'error|proxy|timed out' | head -1)"
fi

# 4) 项目能跑
v=$(python3 -c "import requests; print(requests.__version__)" 2>&1 | tail -1)
if [ "$v" = "2.31.0" ]; then
  ok "项目自检" "requests $v"
else
  bad "项目自检" "$v"
fi

if [ -n "$proxy_env$pip_proxy" ] && [ "$code" = "200" ] && [ $prc -eq 0 ] && [ "$v" = "2.31.0" ]; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
