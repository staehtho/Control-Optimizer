import pytest

from utils.formating import str2array, expr2array, array2expr


@pytest.mark.parametrize(
    "string, expected",
    [
        ("1, 2, 3", [1.0, 2.0, 3.0]),
        ("1 2 3", [1.0, 2.0, 3.0]),
        ("1; 2; 3", [1.0, 2.0, 3.0]),
        ("1.8 2.8, 3.4", [1.8, 2.8, 3.4]),
        ("", []),
        ("abc", []),
    ],
)
def test_str2array(string, expected):
    assert str2array(string) == expected

@pytest.mark.parametrize(
    "expr, expected",
    [
        ("(s + 1)^2", [1, 2, 1]),
        ("s*(s + 1)", [1, 1, 0]),
        ("s(s + 1)(s + 2)", [1, 3, 2, 0]),
        ("s(s+1)(s+2)", [1, 3, 2, 0]),
    ]
)
def test_expr2array(expr, expected):
    assert expr2array(expr) == expected

@pytest.mark.parametrize(
    "expr, expected",
    [
        ([1, 2, 1], "(s + 1)**2"),
        ([1, 3, 3, 1], "(s + 1)**3"),
        ([1, 1, 0], "s(s + 1)"),
        ([1, 1.2, 1], "(s**2 + 1.2*s + 1)")
    ]
)
def test_array2binominal(expr, expected):
    assert array2expr(expr) == expected
