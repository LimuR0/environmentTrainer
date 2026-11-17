# 报告生成器

项目要求机器上装有 `cowsay`（用来给 CI 日志生成 ASCII 小图）。

```bash
cowsay "build passed"
```

> 现在 `apt-get install -y cowsay` 报 `E: Unable to locate package cowsay`，
> 但网络是通的 —— 先去看看 apt 的源配置。
