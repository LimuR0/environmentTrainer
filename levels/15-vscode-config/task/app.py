"""课程示例：一个带测试的小模块。"""


def magic_avg(values):
    """返回平均值；空列表返回 0。"""
    if not values:
        return 0.0
    return sum(values) / len(values)


def main():
    print("avg:", magic_avg([1, 2, 3, 4, 10]))


if __name__ == "__main__":
    main()
