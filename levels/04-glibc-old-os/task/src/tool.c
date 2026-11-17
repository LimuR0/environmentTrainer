/*
 * tool.c —— 一个小工具。
 * CI 在 Ubuntu 24.04（glibc 2.39）上编译，产物直接拷进了 Ubuntu 22.04（glibc 2.35）。
 * 注意 strlcpy：它是 glibc 2.38 才加进来的，所以那个二进制一启动就找不到符号。
 */
#include <stdio.h>
#include <string.h>

#if !defined(__GLIBC__) || (__GLIBC__ < 2) || (__GLIBC__ == 2 && __GLIBC_MINOR__ < 38)
/* 老 glibc 没有 strlcpy，补一个等价实现 —— 所以在旧系统上重新编译完全没问题 */
static size_t strlcpy(char *dst, const char *src, size_t size)
{
    size_t len = strlen(src);
    if (size > 0) {
        size_t n = (len < size - 1) ? len : size - 1;
        memcpy(dst, src, n);
        dst[n] = '\0';
    }
    return len;
}
#endif

int main(void)
{
    char banner[64];
    strlcpy(banner, "TOOL OK: v1.4", sizeof banner);
    printf("%s\n", banner);
    return 0;
}
