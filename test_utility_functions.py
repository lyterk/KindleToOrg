#!/usr/bin/env python3

from fractions import Fraction

from utility_functions import roman_to_float


def test_roman_to_float():
    t = "XVII"
    u = "cc"
    v = "mmxx"

    assert roman_to_float(t) == Fraction(17, 10_000)
    assert roman_to_float(u) == Fraction(1, 50)
    assert roman_to_float(v) == Fraction(101, 500)
    assert roman_to_float(11) == 11
    assert roman_to_float("j") is None
