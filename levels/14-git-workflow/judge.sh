#!/usr/bin/env bash
# 第 14 关判题：身份、合并、忽略规则、提交状态
cd /work/app 2>/dev/null || { echo "CHECK|fail|工作目录|/work/app 不存在"; echo "RESULT|fail"; exit 1; }
ok()  { echo "CHECK|ok|$1|$2"; }
bad() { echo "CHECK|fail|$1|$2"; }

# 1) 提交身份
name=$(git config user.name 2>/dev/null || true)
email=$(git config user.email 2>/dev/null || true)
if [ -n "$name" ] && [ -n "$email" ]; then
  ok "提交身份" "$name <$email>"
else
  bad "提交身份" "user.name / user.email 没配（git config --global user.name ...）"
fi

# 2) 合并必须完成
if [ -f .git/MERGE_HEAD ]; then
  bad "合并状态" "还有未完成的 merge（.git/MERGE_HEAD 存在）"
else
  ok "合并状态" "没有未完成的合并"
fi

# 3) 冲突标记必须清干净
conflicts=$(grep -rIl --exclude-dir=.git -E '^(<<<<<<<|=======|>>>>>>>)' . 2>/dev/null | head -5)
if [ -z "$conflicts" ]; then
  ok "冲突标记" "文件里没有残留标记"
else
  bad "冲突标记" "$(echo "$conflicts" | tr '\n' ' ')"
fi

# 4) 两边的内容都要在（不只是删掉冲突标记）
if grep -q 'login' src/login.js 2>/dev/null && grep -q 'health' src/login.js 2>/dev/null; then
  ok "冲突解决质量" "login() 和 health() 都保留了"
else
  bad "冲突解决质量" "login() / health() 只留下了一个 —— 冲突不是二选一，是合起来"
fi

# 5) node_modules 不能还在索引里
tracked=$(git ls-files | grep -c '^node_modules/' || true)
if [ "$tracked" = "0" ]; then
  ok "索引清理" "node_modules 已从索引移除"
else
  bad "索引清理" "还有 $tracked 个 node_modules 下的文件被跟踪（git rm -r --cached）"
fi

# 6) .gitignore 要真的忽略它
if grep -qE '^/?node_modules/?$' .gitignore 2>/dev/null; then
  ok "忽略规则" ".gitignore 里有 node_modules"
else
  bad "忽略规则" ".gitignore 里没有 node_modules"
fi
if [ -d node_modules ] && git check-ignore -q node_modules; then
  ok "忽略生效" "git check-ignore 确认被忽略"
else
  [ -d node_modules ] || bad "忽略生效" "node_modules 目录不见了（不该删它）"
fi

# 7) 工作区干净
dirty=$(git status --porcelain | head -5)
if [ -z "$dirty" ]; then
  ok "工作区" "干净"
else
  bad "工作区" "还有未提交的改动：$(echo "$dirty" | tr '\n' ' ')"
fi

pass=1
[ -n "$name" ] && [ -n "$email" ] || pass=0
[ -f .git/MERGE_HEAD ] && pass=0
[ -z "$conflicts" ] || pass=0
grep -q 'login' src/login.js 2>/dev/null && grep -q 'health' src/login.js 2>/dev/null || pass=0
[ "$tracked" = "0" ] || pass=0
grep -qE '^/?node_modules/?$' .gitignore 2>/dev/null || pass=0
[ -z "$dirty" ] || pass=0

if [ "$pass" = "1" ]; then
  echo "RESULT|pass"; exit 0
fi
echo "RESULT|fail"; exit 1
