#!/usr/bin/env bash
# 在镜像里造出一个"有历史、有冲突、有误提交"的仓库
set -euo pipefail
cd /work/app

git init -q -b main
git config user.name "Course Bot"
git config user.email "bot@example.com"

git add -A
git commit -q -m "chore: init project"

# 有人把 node_modules 也提交了（经典操作）
mkdir -p node_modules/left-pad node_modules/is-odd
printf 'module.exports = function leftPad(s, n) { return String(s).padStart(n); };\n' > node_modules/left-pad/index.js
printf '{"name":"left-pad","version":"1.3.0"}\n' > node_modules/left-pad/package.json
printf 'module.exports = function isOdd(n) { return n %% 2 === 1; };\n' > node_modules/is-odd/index.js
printf '{"name":"is-odd","version":"3.0.1"}\n' > node_modules/is-odd/package.json
git add -A
git commit -q -m "chore: add dependencies"

# 功能分支
git checkout -q -b feature/login
cat > src/login.js <<'JS'
function greet(name) {
  return `hello, ${name}`;
}

function login(user, password) {
  if (!user || !password) return { ok: false, reason: "missing credentials" };
  return { ok: true, user };
}

module.exports = { greet, login };
JS
cat > README.md <<'MD'
# demo-app

一个很小的示例项目。

## 功能
- greet(name)
- login(user, password)
MD
git commit -q -am "feat: add login()"

# main 上也改了同样的文件，制造冲突
git checkout -q main
cat > src/login.js <<'JS'
function greet(name) {
  return `hello, ${name}`;
}

function health() {
  return { status: "ok" };
}

module.exports = { greet, health };
JS
cat > README.md <<'MD'
# demo-app

一个很小的示例项目。

## 功能
- greet(name)
- health()
MD
git commit -q -am "feat: add health()"

# 抹掉身份配置，让学员自己配（否则 commit 会失败）
git config --unset user.name
git config --unset user.email

echo "--- 仓库状态 ---"
git log --oneline --all --graph | head -10
git status --short | head
