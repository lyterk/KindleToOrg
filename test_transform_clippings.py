#!/usr/bin/env ipython

from transform_clippings import *
from pprint import pprint

test_sections = """The Lord of the Rings (J. R. R. Tolkien)
- Your Note on Location 16415 | Added on Wednesday, September 25, 2019 10:59:56 PM

Translate
==========
The Lord of the Rings (J. R. R. Tolkien)
- Your Highlight on Location 16415-16415 | Added on Wednesday, September 25, 2019 10:59:56 PM

dwimmerlaik,
==========
The Lion, The Witch, and the Wardrobe
- Your Note on Location 15247 | Added on Sunday, October 6, 2019 8:19:20 AM

Heh
==========
The Lion, The Witch, and the Wardrobe
- Your Highlight on Location 15245-15247 | Added on Sunday, October 6, 2019 8:19:20 AM

Edmund did something bad
==========
Verses (Christ, Jesus)
- Your Highlight on page 331-335 | Location 5365-5366 | Added on Tuesday, June 16, 2020 1:14:43 AM

Jesus wept
=========="""


def test_roman_to_float():
    t = "XVII"
    u = "cc"
    v = "mmxx"

    assert roman_to_float(t) == Fraction(17, 10_000)
    assert roman_to_float(u) == Fraction(1, 50)
    assert roman_to_float(v) == Fraction(101, 500)
    assert roman_to_float(11) == 11
    assert roman_to_float("j") is None


def test_get_title_author_series():
    tas = "Prince Caspian (Chronicles of Narnia) (C.S. Lewis)"
    ta = "Prince Caspian (C.S. Lewis)"
    t = "Prince Caspian "

    (title, author, series) = get_title_author_series(tas)
    assert title == "Prince Caspian"
    assert "C.S. Lewis" == author
    assert "Chronicles of Narnia" == series

    (title, author, series) = get_title_author_series(ta)
    assert "Prince Caspian" == title
    assert "C.S. Lewis" == author

    (title, author, series) = get_title_author_series(t)
    assert "Prince Caspian" == title
    assert "Unknown" == author


def test_get_date():
    s = "Added on Sunday, August 5, 2018 4:24:07 PM"
    dt = get_date(s)
    assert dt.day == 5
    assert dt.year == 2018
    assert dt.hour == 16


def test_page_or_location():
    a = "- Your Highlight on page 1"
    b = "Location 1-2"
    c = "- Your Highlight on Location 1-2"

    ax = page_or_location(a)
    assert ax[0] == 1 and ax[1] == None
    bx = page_or_location(b)
    assert bx[0] == 1 and bx[1] == 2
    cx = page_or_location(c)
    assert cx[0] == 1 and cx[1] == 2


def test_from_kindle():
    section: List[str] = test_sections.split("==========")[1]
    # r: List[Annotation] = parse(sections)
    annot: Annotation = Annotation.from_kindle(section)
    assert annot.selection == "dwimmerlaik,"
    assert annot.atype == AType.Highlight


def test_parse_kindle():
    sections: List[str] = test_sections.split("==========")[0:-1]
    r: List[Annotation] = parse_kindle(sections)
    pprint(r)
    # I wish there was some kind of way to correctly do this destructuring assignment, doesn't seem like it though.
    first, second, third = r[0], r[1], r[2]
    assert first.atype == AType.Note
    assert first.selection == "dwimmerlaik,"
    assert second.atype == AType.Note
    assert "Edmund" in second.selection
    assert third.atype == AType.Highlight
    assert third.location == (5365, 5366)
    assert third.page_number == (331, 335)


def test_lt():
    l = [
        Annotation(
            atype=AType.Highlight,
            title="Shogun",
            author="James Clavell",
            series=None,
            page_number=(121, None),
            location=(1842, 1842),
            creation_date=datetime(2020, 5, 10, 13, 8, 22),
            selection="gloaming",
            my_note=None,
            status=Todo.Todo,
            body="",
            other_props={},
        ),
        Annotation(
            atype=AType.Bookmark,
            title="The Stone Sky",
            author="N.K. Jemisin",
            series="Angry Earth",
            page_number=(None, None),
            location=(5141, None),
            creation_date=datetime(2019, 3, 15, 18, 16, 20),
            selection=None,
            my_note=None,
            status=Todo.Todo,
            body="",
            other_props={},
        ),
        Annotation(
            atype=AType.Bookmark,
            title="The Stone Sky",
            author="N.K. Jemisin",
            series="Angry Earth",
            page_number=(None, None),
            location=(2741, None),
            creation_date=datetime(2019, 3, 15, 18, 15, 44),
            selection=None,
            my_note=None,
            status=Todo.Todo,
            body="",
            other_props={},
        ),
        Annotation(
            atype=AType.Bookmark,
            title="The Stone Sky",
            author="N.K. Jemisin",
            series="Angry Earth",
            page_number=(None, None),
            location=(2681, None),
            creation_date=datetime(2018, 12, 11, 17, 43, 54),
            selection=None,
            my_note=None,
            status=Todo.Todo,
            body="",
            other_props={},
        ),
    ]
    l.sort()
    assert l[0].title == "Shogun"
    assert l[1].location[0] == 2681
    assert l[3].location[0] == 5141


def test_merge_todo():
    t = Todo.Todo
    u = Todo.Done
    # Should advance, there's been progression.
    assert t._merge(u) == Todo.Done

    w = Todo.CheckWait
    c = Todo.Checked
    # Should advance, there's been progression.
    assert w._merge(c) == Todo.Checked

    # Should stay as is, it's already further advanced.
    assert c._merge(w) == Todo.Checked

    # Should advance from checking to todos
    assert c._merge(t) == Todo.Todo
    # Should stay as, equality just means nothing changes.
    assert t._merge(t) == Todo.Todo


def test_book_merge():
    pass


def test_merge_org():
    pass


def test_author_merge():
    pass


def test_compare_books():
    books = parse_kindle(test_sections.split("==========")[0:-1])
    sb = set(books)

    # assert sb == set()


def test_end_to_end():
    with open(file_location, "r") as f:
        file_str = f.read()

    authors = parse_kindle(file_str)

    org_lines = [author.to_org() for author in authors.values()]

    with open("books.org", "w") as f:
        f.write("\n".join(org_lines))

    assert True is True


def test_read_org():
    with open("test_cases/author_test_case.org", "r") as f:
        file_str = f.read()

    authors = parse_org(file_str)

    assert authors == {}
