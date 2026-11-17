/*
 * mathlib.c —— 一个很简单的共享库，release 页面只提供 x86_64 的预编译产物。
 * 源码是跨架构的：在任何平台上重新编译都能得到正确结果。
 */
double magic_avg(const double *xs, int n)
{
    if (n <= 0) return 0.0;
    double sum = 0.0;
    for (int i = 0; i < n; i++) sum += xs[i];
    return sum / n;
}

double magic_double(double x)
{
    return x * 2.0;
}
