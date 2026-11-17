/**
 * 项目验收脚本：依赖树里必须是一套能跟 React 18 共存的 UI 库。
 * 只查版本与 peer 约束，不渲染真实 DOM。
 */
const path = require("path");

function pkg(name) {
  try {
    return require(path.join(name, "package.json"));
  } catch (e) {
    return null;
  }
}

let failed = false;
function check(label, ok, detail) {
  console.log(`${ok ? "✓" : "✗"} ${label}${detail ? "  " + detail : ""}`);
  if (!ok) failed = true;
}

const react = pkg("react");
check("react 已安装", !!react, react ? react.version : "缺失");
check("react 是 18.x", !!react && react.version.startsWith("18."), react ? react.version : "");

const legacy = pkg("@material-ui/core");
check("已移除只支持 React 16/17 的 @material-ui/core", !legacy, legacy ? legacy.version : "");

const mui = pkg("@mui/material");
check("@mui/material 已安装", !!mui, mui ? mui.version : "缺失");
if (mui) {
  const peer = (mui.peerDependencies || {}).react || "";
  check("@mui/material 的 peer 接受 React 18", /18|\*/.test(peer), `peer react=${peer}`);
}

const emotion = pkg("@emotion/react");
check("@mui/material 的 peer @emotion/react 已安装", !!emotion, emotion ? emotion.version : "缺失");

const styled = pkg("@emotion/styled");
check("@mui/material 的 peer @emotion/styled 已安装", !!styled, styled ? styled.version : "缺失");

const pd = pkg("react-dom");
check("react-dom 与 react 同版本", !!pd && !!react && pd.version === react.version, pd ? pd.version : "缺失");

if (failed) {
  console.log("\n依赖树还不能一起工作");
  process.exit(1);
}
console.log("\nVERIFY OK");
