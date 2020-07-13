#!/usr/bin/env ipython

from fractions import Fraction
from sys import maxsize
from typing import TypeVar, Callable, Any, ByteString, Optional, Union, Set, List


# Utility functions
S = TypeVar("S")


def head(l: List[S]) -> Optional[S]:
    try:
        return l[0]
    except IndexError:
        return None


def parse_tags(heading: str) -> Set[str]:
    return set(heading.split(":"))


utf8: Callable[[Any], ByteString] = lambda o: bytes(str(o), "utf-8")


def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value


def roman_to_float(s: Optional[Union[str, int]]) -> Optional[Union[Fraction, int]]:
    """If it's actually an int, or None, pop it back out, otherwise turn it to a
float that's 1/10_000th of its roman value so it sorts at the bottom."""
    if isinstance(s, int):
        return s

    if not s:
        return None

    rom_val = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    int_val = 0
    s = s.upper()
    for i in range(len(s)):
        if i > 0 and rom_val.get(s[i], -maxsize) > rom_val.get(s[i - 1], -maxsize):
            int_val += rom_val.get(s[i], -maxsize) - 2 * rom_val.get(s[i - 1], -maxsize)
        else:
            int_val += rom_val.get(s[i], -maxsize)

    if int_val < 0:
        # Not a roman numeral, treat as invalid input
        return None

    return Fraction(int_val, 10_000)
