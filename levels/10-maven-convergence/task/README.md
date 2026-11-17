# envdemo (Maven)

一个很小的 Java 工具类，用到了 commons-text / commons-lang3。

```bash
mvn -o -q dependency:tree      # 看依赖树
mvn -o test                    # 跑测试
mvn -o -q exec:java -Dexec.mainClass=com.example.App
```

> CI 里加了 enforcer 的 dependencyConvergence 规则，现在构建一直失败。
