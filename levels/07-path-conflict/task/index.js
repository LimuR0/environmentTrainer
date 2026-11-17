const version = process.versions.node;
const major = Number(version.split(".")[0]);

if (major < 20) {
  console.error(`[x] 当前 node v${version}，本项目要求 >= 20.6（--env-file 是 20.6 引入的）`);
  process.exit(1);
}

const name = process.env.APP_NAME || "env-demo";
console.log(`STARTED ${name} on node v${version}`);
