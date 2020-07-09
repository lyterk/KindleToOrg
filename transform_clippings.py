#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from fractions import Fraction
from hashlib import sha256, md5
from itertools import islice, groupby
from math import inf
from re import sub as re_sub, findall as re_findall
from orgparse import loads as org_loads
from orgparse.node import OrgNode
from os import path, environ
from pathlib import Path
from sys import maxsize
from typing import (
    List,
    Dict,
    Tuple,
    Optional,
    Union,
    Iterable,
    Set,
    Any,
    TypeVar,
    Type,
    Callable,
    ByteString,
)


# Static constants
file_location = path.expanduser("~/org/resources/kindle_clippings.txt")
KINDLE_SEPARATOR: str = "=========="

# Type definitions
PageRange = Tuple[Union[str, int], Optional[Union[str, int]]]
LocationRange = Tuple[int, Optional[int]]
DateTime = datetime
Hash = int
Heading = str
BookTitle = str
AuthorName = str
Series = str
IsNoteCollated = bool
Properties = Dict[str, Any]
# Create a generic variable that can be 'Parent', or any subclass.


# Enums
class AType(Enum):
    Highlight = "Highlight"
    Note = "Note"
    Bookmark = "Bookmark"


S = TypeVar("S", bound="Todo")


class Todo(Enum):
    Unchecked = "[ ]"
    Checked = "[X]"
    CheckStart = "[-]"
    CheckWait = "[?]"
    Todo = "TODO"
    Strt = "STRT"
    Proj = "PROJ"
    Wait = "WAIT"
    Hold = "HOLD"
    Done = "DONE"
    Kill = "KILL"
    NoTodo = ""

    def _merge(self: S, other: S) -> S:
        """Define a concrete order for todo values, always pick the more advanced one
        for merge conflicts."""
        order = [
            "",
            "[ ]",
            "[-]",
            "[?]",
            "[X]",
            "TODO",
            "STRT",
            "PROJ",
            "WAIT",
            "HOLD",
            "DONE",
            "KILL",
        ]

        if order.index(self.value) < order.index(other.value):
            # advance the status to a higher stage of completion.
            return other
        else:
            # for explicitness
            return self


# Utility functions
def parse_todo(node: OrgNode) -> Tuple[Todo, Heading]:
    if node.todo:
        return (Todo(node.todo), node.heading)
    else:
        if node.heading.startswith("["):
            try:
                return (Todo(node.heading[0:3]), node.heading[5:])
            except ValueError:
                raise Exception(
                    f"This org node does not have a valid todo action: {node.heading[0:3]}"
                )
        else:
            return (Todo.NoTodo, node.heading)


def window(seq: Iterable, n=2) -> Iterable:
    "Returns a sliding window (of width n) over data from the iterable"
    "   s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...                   "
    it = iter(seq)
    result = tuple(islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result


utf8: Callable[[Any], ByteString] = lambda o: bytes(str(o), "utf-8")


def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value


def write_properties(d: Dict[str, Union[int, str]]) -> str:
    props = [f":{key.upper()}: {value}" for key, value in d.items() if value]
    if len(props) > 0:
        props = "\n" + "\n".join(props) + "\n"
    else:
        props = "\n"
    return f"\n:PROPERTIES:{props}:END:\n"


def roman_to_float(s: Optional[Union[str, int]]) -> Optional[Union[Fraction, int]]:
    """If it's actually an int, or None, pop it back out, otherwise turn it to a
float that's 1/100th of its roman value so it sorts at the bottom."""
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


W = TypeVar("W", bound="BaseOrg")


@dataclass
class BaseOrg:
    status: Optional[Todo] = Todo.Unchecked
    body: Optional[str] = ""
    other_props: Dict[str, Any] = field(default_factory=dict)

    def _org_merge(self, other: BaseOrg) -> None:
        self_todo, other_todo = self.status or Todo.NoTodo, other.status or Todo.NoTodo
        final_status = self_todo._merge(other_todo)

        sbody, obody = self.body or "", other.body or ""
        if sbody.strip() == obody.strip():
            final_body: str = sbody.strip()
        else:
            final_body = sbody.strip() + obody.strip()

        final_props = {**self.other_props, **other.other_props}
        self.status = final_status
        self.body = final_body
        self.other_props = final_props


T = TypeVar("T", bound="Annotation")


@dataclass
class Annotation(BaseOrg):
    atype: AType = AType.Bookmark
    title: BookTitle = ""
    author: AuthorName = ""
    series: Optional[Series] = None
    page_number: Optional[PageRange] = None
    location: Optional[LocationRange] = None
    creation_date: DateTime = datetime.now()
    selection: Optional[str] = None
    my_note: Optional[str] = None

    def __lt__(self, other) -> bool:
        """For sorting"""
        if self.author != other.author:
            return self.author.lower() < other.author.lower()

        rex = r"^the |a "
        self_title = re_sub(rex, "", self.title.lower())
        other_title = re_sub(rex, "", other.title.lower())
        if self_title != other_title:
            return self_title < other_title

        neg_inf: int = -maxsize
        if self.page_number != other.page_number:
            if self.page_number:
                self_page = roman_to_float(self.page_number[0]) or -1
            else:
                self_page = neg_inf

            if other.page_number:
                other_page = roman_to_float(other.page_number[0]) or -1
            else:
                other_page = neg_inf

            return self_page < other_page

        if self.location != other.location:
            if self.location:
                self_location = self.location[0] or -1
            else:
                self_location = neg_inf

            if other.location:
                other_location = other.location[0] or -1
            else:
                other_location = neg_inf

            return self_location < other_location
        else:
            return self.creation_date < other.creation_date
        return False

    def __eq__(self, other: Annotation) -> bool:  # type: ignore[override]
        return (
            self.title == other.title
            and self.location == other.location
            and self.page_number == other.page_number
        )

    def __hash__(self) -> int:
        m = md5()
        for f in [
            self.page_number,
            self.location,
            self.atype.name,
            self.selection,
            self.my_note,
            self.creation_date,
            self.status.name,
            self.body,
        ]:
            m.update(utf8(f))
        for k, v in self.other_props.items():
            m.update(utf8(str(k) + str(v)))
        return int(m.hexdigest(), 16)

    def _merge_note_with_highlight(
        self, previous: Optional[Annotation]
    ) -> Tuple[IsNoteCollated, Annotation]:
        """Notes are sometimes (but it seems not always) followed by a
        highlight that defines how the note was highlighted. I'm not sure
        why this needed to be this way, but whatever."""
        is_collated: IsNoteCollated = False

        # Run checks to make sure that this qualifies as a note to be collated with the previous.
        if not previous:
            return is_collated, self

        if not (self.atype == AType.Highlight and previous.atype == AType.Note):
            # Doesn't fit our pattern for combining notes
            return is_collated, self

        if not (self.title == previous.title):
            # Not the same book
            return is_collated, self

        same_location: bool = False
        if self.location and previous.location:
            if self.location[1] == previous.location[0]:
                same_location = True

        if not same_location:
            return is_collated, self

        self.my_note = previous.my_note
        self.atype = AType.Note
        is_collated = True
        return is_collated, self

    @classmethod
    def from_kindle(cls: Type[T], raw_kindle: str) -> T:
        # Long version: - Your Highlight on page 253 | Location 3870-3870 | Added on Sunday, September 16, 2018 10:39:43 PM
        # Short version bookmark: - Your Bookmark on page 216 | Added on Monday, August 13, 2018 8:47:47 PM
        # Short version highlight: - Your Highlight on Location 1430-1432 | Added on Thursday, June 11, 2020 11:34:35 PM
        lines: List[str] = [i for i in raw_kindle.split("\n") if i]
        metadata_items = [i.strip() for i in lines[1].split("|")]
        page_loc: str = metadata_items[0]
        atype: Optional[AType] = None
        creation_date: Optional[datetime] = None
        selection: Optional[str] = None
        my_note: Optional[str] = None

        page_number: Optional[PageRange] = None
        location: Optional[LocationRange] = None
        title, author, series = get_title_author_series(lines[0])

        if "Bookmark" in page_loc:
            atype = AType.Bookmark
        elif "Note" in page_loc:
            atype = AType.Note
        else:
            atype = AType.Highlight

        remaining: List[str] = []
        if len(lines) > 2:
            remaining = [i for i in lines[2:] if i]

        if atype == AType.Note:
            my_note = "\n".join(remaining).strip() if remaining else None
        elif atype == AType.Highlight:
            selection = "\n".join(remaining).strip() if remaining else None

        if len(metadata_items) == 2:
            creation_date = get_date(metadata_items[1])
            if "Location" in page_loc:
                location = page_or_location(page_loc)
            elif "page" in page_loc:
                page_number = page_or_location(page_loc)

        elif len(metadata_items) >= 3:
            loc_str = metadata_items[1]

            page_number = page_or_location(page_loc)
            location = page_or_location(loc_str)
            creation_date = get_date(metadata_items[2])

        if not creation_date:
            raise Exception("No creation date provided, that's weird")

        annotation: T = cls(
            atype=atype,
            title=title,
            author=author,
            series=series,
            page_number=page_number,
            location=location,
            creation_date=creation_date,
            selection=selection,
            my_note=my_note,
        )
        return annotation

    def to_org(self, depth: int) -> str:
        props = {}
        if self.page_number:
            lp, rp = self.page_number
            if lp or rp:
                if lp and rp:
                    props["page"] = f"{lp}-{rp}"
                else:
                    props["page"] = f"{lp}"

        if self.location:
            ll, rl = self.location
            if ll or rl:
                if ll and rl:
                    props["location"] = f"{ll}-{rl}"
                else:
                    props["location"] = f"{ll}"

        props["note"] = self.my_note
        props["highlight"] = self.selection
        props["creation_date"] = str(self.creation_date)
        all_props = {**props, **self.other_props}
        # checkbox = f"{'[ ]' if self.atype != AType.Bookmark else ''}"
        return f"""{'*' * depth} {self.status.value} {self.atype.name}{write_properties(props)}{self.body}"""

    @classmethod
    def from_org(cls: Type[T], node: OrgNode) -> T:
        status, atype = parse_todo(node)
        props = node.properties
        title: BookTitle = props.get("TITLE")
        author: AuthorName = props.get("AUTHOR")
        series: Optional[Series] = props.get("SERIES")
        creation_date: DateTime = datetime.fromisoformat(props.get("CREATION_DATE"))
        page: Optional[PageRange] = page_or_location(props.get("PAGE"))
        location: Optional[LocationRange] = page_or_location(props.get("LOCATION"))
        selection: Optional[str] = props.get("HIGHLIGHT")
        my_note: Optional[str] = props.get("NOTE")
        # Remove redundant props from props dict
        for s in [
            "TITLE",
            "AUTHOR",
            "SERIES",
            "CREATION_DATE",
            "PAGE",
            "LOCATION",
            "HIGHLIGHT",
            "NOTE",
        ]:
            try:
                del props[s]
            except KeyError:
                pass
        return cls(
            atype=AType(atype),
            title=title,
            author=author,
            series=series,
            page_number=page,
            location=location,
            selection=selection,
            my_note=my_note,
            creation_date=creation_date,
            status=Todo(node.todo),
            body=node.body if node.body else None,
            other_props=props,
        )


U = TypeVar("U", bound="Book")


@dataclass
class Book(BaseOrg):
    title: BookTitle = ""
    author: AuthorName = ""
    series: Optional[Series] = None
    annotations: List[Annotation] = field(default_factory=list)

    def __hash__(self):
        m = md5()
        for n in [self.title, self.author, self.series, self.body]:
            m.update(utf8(n))
        for a in self.annotations:
            ah = hash(a)
            m.update(utf8(ah))
        return int(m.hexdigest(), 16)

    def __repr__(self):
        atypes = [
            i.name
            for i in sorted([i.atype for i in self.annotations], key=lambda a: a.value)
        ]
        groups = groupby(atypes)
        friendly = {k: len(list(g)) for k, g in groups}
        return f"Book(title: {self.title}, total: {len(atypes)}, breakdown: {friendly})"

    def to_org(self, depth: int) -> str:
        props = {
            "author": self.author,
            "series": self.series,
            "id": hash(self),
            **self.other_props,
        }
        first_line = f"""{'*' * depth}{' ' + self.status.value if self.status else ''} {self.title} [/]"""
        props_lines = f"""{write_properties(props)}"""
        body_lines = f"""{self.body if self.body else ''}"""
        return (
            first_line
            + props_lines
            + body_lines
            + "\n".join([a.to_org(depth + 1) for a in self.annotations])
        )

    def _merge(self, other: Book) -> None:
        self_set: Set[Annotation] = set(self.annotations)
        other_set: Set[Annotation] = set(other.annotations)

        results: List[Annotation] = list(self_set.intersection(other_set))

        def _determine_merge(
            curr: Annotation, left: Set[Annotation], right: Set[Annotation]
        ) -> Annotation:
            to_check: Set[Annotation]
            if curr in left:
                to_check = right
            else:
                to_check = left

            for other_anno in to_check:
                merged_result: Annotation
                # Equality is shallower than hashing. Doesn't check org data.
                if curr == other_anno:
                    # Merge in all updated org data.
                    curr._org_merge(other_anno)
                    break
            return curr

        for exclusive in self_set.symmetric_difference(other_set):
            result = _determine_merge(exclusive, self_set, other_set)
            results.append(result)

        self._org_merge(other)
        self.annotations = results

    @classmethod
    def from_org(cls: Type[U], node: OrgNode) -> U:
        annotations: List[Annotation] = [
            Annotation.from_org(anode) for anode in node.children
        ]
        author: AuthorName = node.get_property("AUTHOR")
        series: Optional[Series] = node.get_property("SERIES")
        body: str = node.body.strip() if node.body.strip() else None
        for p in ["AUTHOR", "SERIES"]:
            try:
                del node.properties[p]
            except KeyError:
                pass
        status, book_title = parse_todo(node)
        book: U = cls(
            title=book_title,
            author=author,
            series=series,
            annotations=annotations,
            body=body,
            status=status,
            other_props=node.properties,
        )
        return book


V = TypeVar("V", bound="Author")


@dataclass
class Author(BaseOrg):
    author_name: AuthorName = ""
    books: Dict[BookTitle, Book] = field(default_factory=dict)
    body: Optional[str] = None

    def __hash__(self):
        m = md5()
        fields = [self.author_name, self.body, self.status.name, self.body]
        for field in fields:
            m.update(utf8(field))
        for key, value in self.other_props.items():
            m.update(utf8(key + str(value)))
        for b in self.books:
            bh = hash(b)
            m.update(utf8(bh))
        return int(m.hexdigest(), 16)

    def to_org(self) -> str:
        depth = 1
        headline = f"""*{' ' + self.status.value if self.status.value else ''} {self.author_name}"""
        properties = f"{write_properties(self.other_props)}"
        bodyline = f"{self.body if self.body else ''}"
        return (
            headline
            + properties
            + bodyline
            + "\n".join([b.to_org(depth + 1) for b in self.books.values()])
        )

    def _merge(self, other: Author) -> None:
        results: Dict[BookTitle, Book] = {}
        if hash(self) != hash(other):
            self_books: Set[BookTitle] = set(self.books.keys())
            other_books: Set[BookTitle] = set(other.books.keys())

            symdiff_books = self_books.symmetric_difference(other_books)
            for book in symdiff_books:
                results[book] = self.books.get(book, other.books[book])

            intersection_books: Set[BookTitle] = self_books.intersection(other_books)
            for book in intersection_books:
                self_book: Book = self.books[book]
                other_book: Book = other.books[book]
                combine_book: Book = self_book._merge(other_book)
                results[book] = combine_book

        self._org_merge(other)
        self.books = results

    @classmethod
    def from_org(cls: Type[V], node: OrgNode) -> V:
        child_books: Dict[BookTitle, Book] = {
            bnode.heading: Book.from_org(bnode) for bnode in node.children
        }
        author: V = cls(
            author=node.heading,
            books=child_books,
            status=parse_todo(node),
            body=node.body.strip() if node.body.strip() else None,
            other_props=node.properties,
        )
        return author


Authors = Dict[AuthorName, Author]


def page_or_location(s: str) -> Union[PageRange, LocationRange]:
    last = s.split(" ")[-1]
    ls = last.split("-")

    def safe_int(s: str) -> Union[str, int]:
        try:
            return int(s)
        except:
            return s

    range_: Union[PageRange, LocationRange] = (
        safe_int(ls[0]),
        None if len(ls) == 1 else safe_int(ls[1]),
    )
    return range_


def get_title_author_series(s: str,) -> Tuple[BookTitle, AuthorName, Optional[Series]]:
    # NOTE This is vulnerable to parens in titles
    # Match everything until parentheses, or until end
    author: Optional[AuthorName] = None
    series: Optional[Series] = None
    title = re_findall(r"(^[^\(]+)", s)[0].strip()
    # Match all things inside parens, returning a list
    regex = r"\(([^\)]+)\)"
    author_series = re_findall(regex, s)

    if len(author_series) == 1:
        author = author_series[0]
    elif len(author_series) == 2:
        # They're in reverse order, series first.
        author, series = author_series[1], author_series[0]

    if not author:
        author = "Unknown"

    return title, author, series


def get_date(s: str) -> DateTime:
    return datetime.strptime(s, "Added on %A, %B %d, %Y %I:%M:%S %p")


def parse_kindle(file_str: str) -> Authors:
    sections: List[str] = file_str.split(KINDLE_SEPARATOR)

    results: List[Annotation] = []
    prev: Optional[Annotation] = None

    curr_already_added: bool = False

    for section in sections:
        filtered: str = "\n".join([i for i in section.split("\n") if i])
        annotation: Annotation = Annotation.from_kindle(filtered)

        is_collated, current = annotation._merge_note_with_highlight(prev)

        if not is_collated:
            if prev and not curr_already_added:
                results.append(prev)
            curr_already_added = False
            prev = current
        elif is_collated:
            results.append(current)
            curr_already_added = True
            is_collated = False

    # Take care of the last one.
    if not is_collated:
        results.append(annotation)

    book_groups = groupby(results, lambda i: i.title)
    books: List[Book] = []
    for key, group in book_groups:
        g = list(group)
        title, author, series = key, g[0].author, g[0].series
        book = Book(title=title, author=author, series=series, annotations=g)
        books.append(book)

    authors: Dict[str, Author] = {}
    for book in books:
        if book.author in authors:
            author.books[book.title] = book
        else:
            author = Author(author_name=book.author)
            author.books[book.title] = book
            authors[author.author_name] = author

    return authors


def parse_org(file_str: str) -> Authors:
    root = org_loads(file_str)
    authors: Authors = {}

    for author_node in root:
        author = Author.from_org(author_node)

        authors[author.author_name] = author

    return authors


# Notes always come before their highlight
if __name__ == "__main__":
    with open(file_location, mode="r") as f:
        fil = f.read()
        # Something to do with how Kindle saves files (endianess)
        # See https://stackoverflow.com/questions/17912307/u-ufeff-in-python-string/17912811#17912811
        fil = fil.replace("\ufeff", "")
        sections = fil.split("==========")[0:-1]

    authors = collect_authors(sections)

    # try:
    #     with open("hashes.json", "r") as f:
    #         extant_hashes = json.load(f)
    # except:
    #     extant_hashes = {}

    # with open("hashes.json", "w") as f:
    #     json.dump(hashes, f, indent=4)

    out_str = "\n".join([author.to_org() for author in authors.values()])
    with open("books.org", "w") as f:
        f.write(out_str)
        pass
