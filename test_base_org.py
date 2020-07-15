#!/usr/bin/env ipython

from base_org import *
from orgparse import loads as org_loads


def test_emacs_dates():
    time = "[2020-01-02 Thu 21:34]"
    date = "<2020-07-12 Sun>"

    assert EmacsDateTime.org_strptime(time).month == 1
    assert EmacsDate.org_strptime(date).day == 12


def test_write_properties():
    props = {"prop_a": 1, "prop_b": "hello"}
    b = BaseOrg(properties=props)

    result = """:PROPERTIES:
:PROP_A: 1
:PROP_B: hello
:END:"""

    assert b.write_properties() == result


def test_parse_org_heading():
    a = org_loads("* [ ] Note [/]").children[0]
    b = org_loads("* [?] Highlight [1234/1234]").children[0]
    c = org_loads("* [X] Note").children[0]

    assert BaseOrg.parse_heading(a) == (Todo.Unchecked, "Note")
    assert BaseOrg.parse_heading(b) == (Todo.CheckWait, "Highlight")

    d = org_loads("* TODO Note [/]").children[0]
    e = org_loads("* DONE Note [1234/1234]").children[0]

    assert BaseOrg.parse_heading(d) == (Todo.Todo, "Note")
    assert BaseOrg.parse_heading(e) == (Todo.Done, "Note")
