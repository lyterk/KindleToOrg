#!/usr/bin/env ipython

from kindle_to_org import *
from base_org import *
from static import *
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
New Testament (Christ, Jesus)
- Your Highlight on page 331-335 | Location 5365-5366 | Added on Tuesday, June 16, 2020 1:14:43 AM

Jesus wept
=========="""


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


# ToOrg tests


def test_annotation_to_org():
    ann = Annotation(
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
        body="Really really long note here.",
        properties={},
    )
    result = """*** TODO Highlight  [0/0]
:PROPERTIES:
:AUTHOR: James Clavell
:CREATION_DATE: 2020-05-10 13:08:22
:HIGHLIGHT: gloaming
:LOCATION: 1842-1842
:PAGE: 121
:TITLE: Shogun
:END:
Really really long note here."""
    assert ann.to_org(3) == result


def test_book_to_org():
    book = Book(
        author="James Clavell", title="Shogun", series="Asia Saga", annotations=[]
    )
    result = """** Shogun  [0/0]
:PROPERTIES:
:AUTHOR: James Clavell
:SERIES: Asia Saga
:END:"""
    print(book.to_org(2))
    assert book.to_org(2) == result


def test_author_to_org():
    author = Author(author_name="James Clavell", body="Some long note here", books={})
    result = """* James Clavell  [0/0]
:PROPERTIES:
:END:
Some long note here"""
    assert author.to_org() == result


def test_author_to_org():
    author = Author(
        heading="",
        status=None,
        body=None,
        org_time=None,
        creation_date=None,
        level=0,
        progress=Progress(num=0, denom=0),
        important_times=[],
        properties={},
        tags=set(),
        author_name="Christ, Jesus",
        books={
            "New Testament": Book(
                heading="",
                status=None,
                body=None,
                org_time=None,
                creation_date=None,
                level=0,
                progress=Progress(num=0, denom=0),
                important_times=[],
                properties={},
                tags=set(),
                title="New Testament",
                author="Christ, Jesus",
                series=None,
                annotations=[
                    Annotation(
                        heading="",
                        status=None,
                        body=None,
                        org_time=None,
                        creation_date=EmacsDateTime(2020, 6, 16, 1, 14, 43),
                        level=0,
                        progress=Progress(num=0, denom=0),
                        important_times=[],
                        properties={},
                        tags=set(),
                        atype=AType.Highlight,
                        title="New Testament",
                        author="Christ, Jesus",
                        series=None,
                        page_number=(331, 335),
                        location=(5365, 5366),
                        selection="Jesus wept",
                        my_note=None,
                    )
                ],
            )
        },
    )


def test_parse_kindle():
    r: List[Annotation] = parse_kindle(test_sections)
    pprint(r)
    # I wish there was some kind of way to correctly do this destructuring assignment, doesn't seem like it though.
    result = {
        "Christ, Jesus": Author(
            heading="",
            status=None,
            body=None,
            org_time=None,
            creation_date=None,
            level=0,
            progress=Progress(num=0, denom=0),
            important_times=[],
            properties={},
            tags=set(),
            author_name="Christ, Jesus",
            books={
                "New Testament": Book(
                    heading="",
                    status=None,
                    body=None,
                    org_time=None,
                    creation_date=None,
                    level=0,
                    progress=Progress(num=0, denom=0),
                    important_times=[],
                    properties={},
                    tags=set(),
                    title="New Testament",
                    author="Christ, Jesus",
                    series=None,
                    annotations=[
                        Annotation(
                            heading="",
                            status=None,
                            body=None,
                            org_time=None,
                            creation_date=EmacsDateTime(2020, 6, 16, 1, 14, 43),
                            level=0,
                            progress=Progress(num=0, denom=0),
                            important_times=[],
                            properties={},
                            tags=set(),
                            atype=AType.Highlight,
                            title="New Testament",
                            author="Christ, Jesus",
                            series=None,
                            page_number=(331, 335),
                            location=(5365, 5366),
                            selection="Jesus wept",
                            my_note=None,
                        )
                    ],
                )
            },
        ),
        "J. R. R. Tolkien": Author(
            heading="",
            status=None,
            body=None,
            org_time=None,
            creation_date=None,
            level=0,
            progress=Progress(num=0, denom=0),
            important_times=[],
            properties={},
            tags=set(),
            author_name="J. R. R. Tolkien",
            books={
                "The Lord of the Rings": Book(
                    heading="",
                    status=None,
                    body=None,
                    org_time=None,
                    creation_date=None,
                    level=0,
                    progress=Progress(num=0, denom=0),
                    important_times=[],
                    properties={},
                    tags=set(),
                    title="The Lord of the Rings",
                    author="J. R. R. Tolkien",
                    series=None,
                    annotations=[
                        Annotation(
                            heading="",
                            status=None,
                            body=None,
                            org_time=None,
                            creation_date=EmacsDateTime(2019, 9, 25, 22, 59, 56),
                            level=0,
                            progress=Progress(num=0, denom=0),
                            important_times=[],
                            properties={},
                            tags=set(),
                            atype=AType.Note,
                            title="The Lord of the Rings",
                            author="J. R. R. Tolkien",
                            series=None,
                            page_number=None,
                            location=(16415, 16415),
                            selection="dwimmerlaik,",
                            my_note="Translate",
                        )
                    ],
                )
            },
        ),
        "Unknown": Author(
            heading="",
            status=None,
            body=None,
            org_time=None,
            creation_date=None,
            level=0,
            progress=Progress(num=0, denom=0),
            important_times=[],
            properties={},
            tags=set(),
            author_name="Unknown",
            books={
                "The Lion, The Witch, and the Wardrobe": Book(
                    heading="",
                    status=None,
                    body=None,
                    org_time=None,
                    creation_date=None,
                    level=0,
                    progress=Progress(num=0, denom=0),
                    important_times=[],
                    properties={},
                    tags=set(),
                    title="The Lion, The Witch, and the Wardrobe",
                    author="Unknown",
                    series=None,
                    annotations=[
                        Annotation(
                            heading="",
                            status=None,
                            body=None,
                            org_time=None,
                            creation_date=EmacsDateTime(2019, 10, 6, 8, 19, 20),
                            level=0,
                            progress=Progress(num=0, denom=0),
                            important_times=[],
                            properties={},
                            tags=set(),
                            atype=AType.Note,
                            title="The Lion, The Witch, and the Wardrobe",
                            author="Unknown",
                            series=None,
                            page_number=None,
                            location=(15245, 15247),
                            selection="Edmund did something bad",
                            my_note="Heh",
                        )
                    ],
                )
            },
        ),
    }
    jesus, tolkien, unknown = r["Christ, Jesus"], r["J. R. R. Tolkien"], r["Unknown"]
    bible = jesus.books["New Testament"]
    assert bible.annotations[0].selection == "Jesus wept"
    lotr = tolkien.books["The Lord of the Rings"]
    assert lotr.annotations[0].selection == "dwimmerlaik,"
    assert lotr.annotations[0].atype == AType.Note
    assert lotr.annotations[0].my_note == "Translate"
    lww = unknown.books["The Lion, The Witch, and the Wardrobe"]
    assert lww.annotations[0].atype == AType.Note
    assert lww.annotations[0].location == (15245, 15247)


def test_progress():
    assert str(Progress(num=1, denom=100)) == "[1/100]"


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
            properties={},
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
            properties={},
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
            properties={},
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
            properties={},
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
    books = parse_kindle(test_sections)
    sb = set(books)

    # assert sb == set()


def test_end_to_end():
    with open(FILE_LOCATION, "r") as f:
        file_str = f.read()

    authors = parse_kindle(file_str)

    org_lines = [author.to_org() for author in authors.values()]

    with open("books.org", "w") as f:
        f.write("\n".join(org_lines))

    assert True is True


def test_parse_book():
    input = """** [X] The Lord of the Rings [1/2]
CLOSED: [2020-07-08 Wed 21:40]
:PROPERTIES:
:AUTHOR: J. R. R. Tolkien
:ID: 553394003499142966
:END:"""
    node = org_loads(input).children[0]
    print(BaseOrg.parse_heading(node))
    assert BaseOrg.parse_heading(node) == (Todo.Checked, "The Lord of the Rings")


def test_read_org():
    with open("test_cases/author_test_case.org", "r") as f:
        file_str = f.read()

    authors = parse_org(file_str)

    result = {
        "J. R. R. Tolkien": Author(
            heading="",
            status=Todo.Checked,
            body=None,
            org_time=None,
            creation_date=None,
            level=0,
            progress=Progress(num=0, denom=0),
            important_times=[],
            properties={},
            tags=set(),
            author_name="J. R. R. Tolkien",
            books={
                "The Hobbit": Book(
                    heading="",
                    status=Todo.Checked,
                    body=None,
                    org_time=None,
                    creation_date=None,
                    level=0,
                    progress=Progress(num=0, denom=0),
                    important_times=[],
                    properties={"ID": "744429718141913008"},
                    tags=set(),
                    title="The Hobbit",
                    author="J. R. R. Tolkien",
                    series=None,
                    annotations=[
                        Annotation(
                            heading="",
                            status=Todo.Checked,
                            body=None,
                            org_time=None,
                            creation_date=EmacsDateTime(2019, 11, 23, 16, 56),
                            level=0,
                            progress=Progress(num=0, denom=0),
                            important_times=[],
                            properties={},
                            tags=set(),
                            atype=Todo.Checked,
                            title=None,
                            author=None,
                            series=None,
                            page_number=None,
                            location=(228, 229),
                            selection="“Of course!” said Bilbo, and sat down in a hurry. He missed the stool and sat in the fender,",
                            my_note=None,
                        )
                    ],
                ),
                "The Lord of the Rings": Book(
                    heading="",
                    status=Todo.Checked,
                    body=None,
                    org_time=None,
                    creation_date=None,
                    level=0,
                    progress=Progress(num=0, denom=0),
                    important_times=[],
                    properties={"ID": "553394003499142966"},
                    tags=set(),
                    title="The Lord of the Rings",
                    author="J. R. R. Tolkien",
                    series=None,
                    annotations=[
                        Annotation(
                            heading="",
                            status=Todo.CheckWait,
                            body=None,
                            org_time=None,
                            creation_date=EmacsDateTime(2019, 9, 23, 20, 9),
                            level=0,
                            progress=Progress(num=0, denom=0),
                            important_times=[],
                            properties={},
                            tags=set(),
                            atype=Todo.CheckWait,
                            title=None,
                            author=None,
                            series=None,
                            page_number=None,
                            location=(15639, 15640),
                            selection="lost. Make haste!’ Flinging on some clothes, Merry looked outside. The world was darkling.",
                            my_note=None,
                        ),
                        Annotation(
                            heading="",
                            status=Todo.Checked,
                            body=None,
                            org_time=None,
                            creation_date=EmacsDateTime(2019, 9, 25, 22, 59),
                            level=0,
                            progress=Progress(num=0, denom=0),
                            important_times=[],
                            properties={},
                            tags=set(),
                            atype=Todo.Checked,
                            title=None,
                            author=None,
                            series=None,
                            page_number=None,
                            location=(16415, 16415),
                            selection="dwimmerlaik,",
                            my_note="Translate",
                        ),
                    ],
                ),
            },
        )
    }
    assert authors == result


def test_empty_files():
    empty_file_str = ""

    assert parse_kindle(empty_file_str) == {}
    assert parse_org(empty_file_str) == {}


def test_super():
    a = Author("Tolkien")


def test_merge_authors():
    with open("test_cases/author_test_case.org", "r") as f:
        file_str = f.read()

    left_authors = parse_org(file_str)
    right_authors = parse_org(file_str)

    assert merge_files(left_authors, right_authors) == left_authors
