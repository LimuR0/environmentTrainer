// main.cpp —— 用到了 C++23 的 <print>，需要 GCC 14+
#include <print>
#include <vector>

int main()
{
    std::vector<double> xs{1.0, 2.0, 3.0, 4.0, 10.0};
    double sum = 0.0;
    for (double x : xs) sum += x;
    const double avg = sum / static_cast<double>(xs.size());

    std::print("COMPUTE OK {:.2f}\n", avg);
    return 0;
}
