# 这个目录是从旧机器整个拷过来的虚拟环境

`tool/` 原本建在 `/tmp/tool`，为了"复用"被直接 `cp -a` 到了 `/work/tool`。

结果：

- `./tool/bin/python` 还能用（它是指向系统 python 的符号链接）
- `./tool/bin/pip` 直接报错：`bad interpreter: /tmp/tool/bin/python: no such file or directory`

## 验收标准

```bash
./tool/bin/pip --version        # 能正常打印 pip 版本，且路径是 /work/tool
./tool/bin/python -c 'import click, sys; print(click.__version__, sys.prefix)'
# 期望：8.1.7 /work/tool
```
