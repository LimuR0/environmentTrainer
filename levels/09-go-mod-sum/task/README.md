# envdemo

生成 UUID 的小工具。CI 是离线环境（`GOPROXY=off`），依赖只能来自本地模块缓存。

```bash
go build ./...
go test ./...
go run .
```

> 昨天往 go.mod 里加了 google/uuid，本地能跑，
> 结果今天 clone 下来 build 一直报 `missing go.sum entry`。
