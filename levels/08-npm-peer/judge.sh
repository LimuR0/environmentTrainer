#!/usr/bin/env bash
# 第 8 关判题：npm 依赖树必须自洽，且 UI 库与 React 18 兼容
cd /work 2>/dev/null || { echo "CHECK|fail|工作目录|/work 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

if [ ! -d node_modules ]; then
  bad "依赖已安装" "node_modules 不存在（先 npm install）"
  echo "RESULT|fail"; exit 1
fi
ok "依赖已安装" "node_modules 存在"

lsout=$(npm ls --depth=0 2>&1); lsrc=$?
if [ $lsrc -eq 0 ]; then
  ok "依赖树" "npm ls 无 ELSPROBLEMS"
else
  first=$(echo "$lsout" | grep -E "ERESOLVE|UNMET|invalid" | head -1)
  bad "依赖树" "${first:-npm ls 返回 $lsrc}"
fi

legacy=$(node -e "try{console.log(require('@material-ui/core/package.json').version)}catch(e){}" 2>/dev/null)
if [ -z "$legacy" ]; then
  ok "旧 UI 库" "@material-ui/core 已移除"
else
  bad "旧 UI 库" "@material-ui/core@$legacy 仍在（v4 只支持 React 16/17）"
fi

mui=$(node -e "try{console.log(require('@mui/material/package.json').version)}catch(e){}" 2>/dev/null)
if [ -n "$mui" ]; then
  ok "新 UI 库" "@mui/material@$mui"
else
  bad "新 UI 库" "没有 @mui/material"
fi

emo=$(node -e "try{console.log(require('@emotion/react/package.json').version)}catch(e){}" 2>/dev/null)
if [ -n "$emo" ]; then
  ok "peer 依赖" "@emotion/react@$emo 已安装"
else
  bad "peer 依赖" "缺 @emotion/react（@mui/material 的 peer）"
fi

vout=$(node verify.js 2>&1); vrc=$?
if [ $vrc -eq 0 ] && echo "$vout" | grep -q "VERIFY OK"; then
  ok "验收脚本" "VERIFY OK"
else
  bad "验收脚本" "$(echo "$vout" | grep '✗' | head -2 | tr '\n' ' ')"
fi

if [ $lsrc -eq 0 ] && [ -z "$legacy" ] && [ -n "$mui" ] && [ -n "$emo" ] && [ $vrc -eq 0 ]; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
