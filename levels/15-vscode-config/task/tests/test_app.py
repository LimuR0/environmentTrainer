from app import magic_avg


def test_magic_avg_basic():
    assert magic_avg([1, 2, 3, 4, 10]) == 4.0


def test_magic_avg_empty():
    assert magic_avg([]) == 0.0
