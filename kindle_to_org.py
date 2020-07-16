#!/usr/bin/env python3
from __future__ import annotations

import getopt
import re
import sys

from copy import copy
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from fractions import Fraction
from hashlib import md5
from itertools import groupby
from orgparse import loads as org_loads
from orgparse.node import OrgNode
from typing import (
    List,
    Dict,
    Tuple,
    Optional,
    Union,
    Set,
    TypeVar,
    Type,
)
from shutil import copyfile

from base_org import BaseOrg, EmacsDateTime, EmacsDate, Todo, Progress
from static import (
    AuthorName,
    BookTitle,
    LocationRange,
    PageRange,
    Heading,
    IsNoteCollated,
    Properties,
    Series,
    KINDLE_SEPARATOR,
)
from utility_functions import roman_to_float, utf8


class AType(Enum):
    Highlight = "Highlight"
    Note = "Note"
    Bookmark = "Bookmark"


N = TypeVar("N", bound="Annotation")


@dataclass
class Annotation(BaseOrg):
    atype: AType = AType.Bookmark
    title: BookTitle = ""
    author: AuthorName = ""
    series: Optional[Series] = None
    page_number: Optional[PageRange] = None
    location: Optional[LocationRange] = None
    # Not optional, but a default value isn't meaningful.
    creation_date: EmacsDateTime = None  # typing: ignore
    selection: Optional[str] = None
    my_note: Optional[str] = None

    def __str__(self) -> str:
        return (
            "Annotation("
            + f"atype=AType.{self.atype.value}, "
            + f'title="{self.title}", '
            + f'author="{self.author}", '
            + f'series="{self.series}", '
            + f"page_number={self.page_number}, "
            + f"location={self.location}, "
            + f'creation_date="{self.creation_date}", '
            + f'selection="{self.selection}", '
            + f'my_note="{self.my_note}")'
        )

    def __lt__(self, other: N) -> bool:
        """For sorting"""
        if self.author != other.author:
            return self.author.lower() < other.author.lower()

        rex = r"^the |a "
        self_title = re.sub(rex, "", self.title.lower())
        other_title = re.sub(rex, "", other.title.lower())
        if self_title != other_title:
            return self_title < other_title

        neg_inf: int = -sys.maxsize
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
        org_hash = super().__hash__()
        for f in [
            self.page_number,
            self.location,
            self.atype.name,
            self.selection,
            self.my_note,
            self.creation_date,
            self.status.name,
            self.body,
            org_hash,
        ]:
            m.update(utf8(f))
        for k, v in self.properties.items():
            m.update(utf8(str(k) + str(v)))
        return int(m.hexdigest(), 16)

    def merge_note_with_highlight(
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
    def from_kindle(cls: Type[N], raw_kindle: str) -> N:
        # Long version: - Your Highlight on page 253 | Location 3870-3870 | Added on Sunday, September 16, 2018 10:39:43 PM
        # Short version bookmark: - Your Bookmark on page 216 | Added on Monday, August 13, 2018 8:47:47 PM
        # Short version highlight: - Your Highlight on Location 1430-1432 | Added on Thursday, June 11, 2020 11:34:35 PM
        lines: List[str] = [i for i in raw_kindle.split("\n") if i]
        metadata_items = [i.strip() for i in lines[1].split("|")]
        page_loc: str = metadata_items[0]
        atype: Optional[AType] = None
        status: Todo = Todo.Unchecked
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
            my_note = "[ |n| ]".join(remaining).strip() if remaining else None
        elif atype == AType.Highlight:
            selection = "[ |n| ]".join(remaining).strip() if remaining else None

        if len(metadata_items) == 2:
            creation_date = EmacsDateTime.kindle_strptime(metadata_items[1])
            if "Location" in page_loc:
                location = page_or_location(page_loc)
            elif "page" in page_loc:
                page_number = page_or_location(page_loc)

        elif len(metadata_items) >= 3:
            creation_date = EmacsDateTime.kindle_strptime(metadata_items[2])
            loc_str = metadata_items[1]

            page_number = page_or_location(page_loc)
            location = page_or_location(loc_str)

        if not creation_date:
            raise Exception("No creation date provided, that's weird")

        annotation: N = cls(
            atype=atype,
            title=title,
            author=author,
            series=series,
            status=status,
            page_number=page_number,
            location=location,
            creation_date=creation_date,
            selection=selection,
            my_note=my_note,
        )
        return annotation

    def to_org(self, depth: int) -> str:
        this = copy(self)
        if this.page_number:
            lp, rp = this.page_number
            if lp or rp:
                if lp and rp:
                    this.properties["page"] = f"{lp}-{rp}"
                else:
                    this.properties["page"] = f"{lp}"

        if this.location:
            ll, rl = this.location
            if ll or rl:
                if ll and rl:
                    this.properties["location"] = f"{ll}-{rl}"
                else:
                    this.properties["location"] = f"{ll}"

        this.properties["note"] = this.my_note
        this.properties["highlight"] = this.selection
        this.properties["creation_date"] = str(this.creation_date)
        this.properties["title"] = this.title
        this.properties["author"] = this.author
        this.heading = this.atype.name

        if this.series:
            this.properties["series"] = this.series

        this.level = depth
        return super(Annotation, this).__str__()

    @classmethod
    def from_org(cls: Type[N], node: OrgNode) -> N:
        status, heading = super().parse_heading(node)
        atype = AType(heading)
        props = node.properties
        title: BookTitle = props.get("TITLE")
        author: AuthorName = props.get("AUTHOR")
        series: Optional[Series] = props.get("SERIES")
        try:
            creation_date: EmacsDateTime = EmacsDateTime.org_strptime(
                props.get("CREATION_DATE")
            )
        except:
            print("Couldn't parse creation date: " + props.get("CREATION_DATE"))
        page: Optional[PageRange] = page_or_location(props.get("PAGE"))
        location: Optional[LocationRange] = page_or_location(props.get("LOCATION"))
        creation_date: Optional[EmacsDateTime] = EmacsDateTime.org_strptime(
            props.get("CREATION_DATE")
        )
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
            atype=atype,
            title=title,
            author=author,
            series=series,
            page_number=page,
            location=location,
            selection=selection,
            my_note=my_note,
            creation_date=creation_date,
            status=status,
            body=node.body if node.body else None,
            properties=props,
        )


B = TypeVar("B", bound="Book")


@dataclass
class Book(BaseOrg):
    title: BookTitle = ""
    author: AuthorName = ""
    series: Optional[Series] = None
    annotations: List[Annotation] = field(default_factory=list)

    def __str__(self) -> str:
        return f"Book(title={self.title}, author={self.author}, series={self.series})"

    def __hash__(self) -> int:
        m = md5()
        org_hash = super().__hash__()
        for n in [self.title, self.author, self.series, self.body, org_hash]:
            m.update(utf8(n))
        for a in self.annotations:
            ah = hash(a)
            m.update(utf8(ah))
        return int(m.hexdigest(), 16)

    def __lt__(self, other: B) -> bool:
        return self.title < other.title

    def __eq__(self, other: B) -> bool:
        return self.title == other.title

    def calc_progress(self) -> Progress:
        return Progress(
            num=len(
                [i for i in self.annotations if i.status in [Todo.Done, Todo.Checked]]
            ),
            denom=len(self.annotations),
        )

    def to_org(self, depth: int) -> str:
        this = copy(self)
        this.heading = this.title
        this.level = depth
        this.show_progress = True
        this.properties["author"] = this.author
        this.properties["series"] = this.series
        this.properties["creation_date"] = this.creation_date
        sorted_children = sorted(this.annotations)
        children = "\n".join([a.to_org(depth + 1) for a in sorted_children])
        return super(Book, this).__str__() + "\n" + children

    def merge(self, other: Book) -> None:
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
    def _get_creation_date(
        self, annotations: List[Annotation]
    ) -> Optional[EmacsDateTime]:
        if annotations:
            return min(
                [anno.creation_date for anno in annotations if anno.creation_date]
            )
        else:
            return None

    @classmethod
    def from_org(cls: Type[B], node: OrgNode) -> B:
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
        status, heading = super().parse_heading(node)
        book: B = cls(
            title=heading,
            author=author,
            series=series,
            creation_date=cls._get_creation_date(annotations),
            body=body,
            status=status,
            properties={key.lower(): value for key, value in node.properties.items()},
            annotations=annotations,
        )
        return book


A = TypeVar("A", bound="Author")


@dataclass
class Author(BaseOrg):
    author_name: AuthorName = ""
    books: Dict[BookTitle, Book] = field(default_factory=dict)

    def __str__(self):
        return f"Author(author_name={self.author_name})"

    def __hash__(self):
        m = md5()
        org_hash = super().__hash__()
        fields = [self.author_name, self.body, self.body, org_hash]
        for field in fields:
            m.update(utf8(field))
        for key, value in self.properties.items():
            m.update(utf8(key + str(value)))
        for b in self.books:
            bh = hash(b)
            m.update(utf8(bh))
        return int(m.hexdigest(), 16)

    def __lt__(self, other: A) -> bool:
        return self.author_name < other.author_name

    def __eq__(self, other: A) -> bool:
        return self.author_name == other.author_name

    def to_org(self) -> str:
        this = copy(self)
        this.level = 1
        this.progress = self.calc_progress()
        this.show_progress = True
        this.heading = this.author_name
        this.properties["creation_date"] = this.creation_date
        sorted_children = sorted([b for b in self.books.values()])
        children = "\n".join([b.to_org(this.level + 1) for b in sorted_children])
        return super(Author, this).__str__() + "\n" + children

    def calc_progress(self) -> Progress:
        num, denom = 0, 0
        for book in self.books.values():
            book.progress = book.calc_progress()
            num += book.progress.num
            denom += book.progress.denom

        return Progress(num=num, denom=denom)

        return Progress(
            num=len(
                [i for i in self.books.values() if i.progress.num != i.progress.denom]
            ),
            denom=len(self.books),
        )

    def merge(self, other: Author) -> None:
        results: Dict[BookTitle, Book] = {}
        if hash(self) != hash(other):
            self_books: Set[BookTitle] = set(self.books.keys())
            other_books: Set[BookTitle] = set(other.books.keys())

            symdiff_books = self_books.symmetric_difference(other_books)
            for book in symdiff_books:
                symbook = self.books.get(book, other.books[book])
                results[book] = symbook

            intersection_books: Set[BookTitle] = self_books.intersection(other_books)

            for book in intersection_books:
                self_book: Book = self.books[book]
                other_book: Book = other.books[book]
                self_book.merge(other_book)
                results[book] = self_book

            self.books = results
        else:
            results = self.books

        self._org_merge(other)
        self.books = results

    @classmethod
    def _get_creation_date(
        self, books: Dict[BookTitle, Book]
    ) -> Optional[EmacsDateTime]:
        if books:
            return min([book.creation_date for book in books.values()])
        else:
            return None

    @classmethod
    def from_org(cls: Type[A], node: OrgNode) -> A:
        child_books: Dict[BookTitle, Book] = {}
        for book_node in node.children:
            book = Book.from_org(book_node)
            child_books[book.title] = book
        status, heading = super().parse_heading(node)
        author: A = cls(
            author_name=heading,
            books=child_books,
            status=status,
            creation_date=cls._get_creation_date(child_books),
            body=node.body.strip() if node.body.strip() else None,
            properties={key.lower(): value for key, value in node.properties.items()},
        )
        return author


Authors = Dict[AuthorName, Author]


def page_or_location(s: str) -> Union[PageRange, LocationRange]:
    if not s:
        return None
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
    # Match everything until parentheses, or until end
    author: Optional[AuthorName] = None
    series: Optional[Series] = None
    title = re.findall(r"(^[^\(]+)", s)[0].strip()
    # Match all things inside parens, returning a list
    regex = r"\(([^\)]+)\)"
    author_series = re.findall(regex, s)

    if len(author_series) == 1:
        author = author_series[0]
    elif len(author_series) == 2:
        # They're in reverse order, series first.
        author, series = author_series[1], author_series[0]

    if not author:
        author = "Unknown"

    return title, author, series


def parse_kindle(file_str: str) -> Authors:
    sections: List[str] = file_str.split(KINDLE_SEPARATOR)[:-1]

    # TODO Just so it's defined, this is ugly, make it optional, figure out how it differs from `current`
    annotation: Annotation = Annotation()

    results: List[Annotation] = []
    prev: Optional[Annotation] = None

    curr_already_added: bool = False
    is_collated: bool = False

    for section in sections:
        filtered: str = "\n".join([i for i in section.split("\n") if i])
        annotation: Annotation = Annotation.from_kindle(filtered)

        is_collated, current = annotation.merge_note_with_highlight(prev)

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

    results.sort()

    book_groups = groupby(results, lambda i: i.title)
    books: List[Book] = []
    for key, group in book_groups:
        g = list(group)
        title, author, series = key, g[0].author, g[0].series
        book = Book(title=title, author=author, series=series, annotations=g)
        books.append(book)

    authors: Dict[AuthorName, Author] = {}
    for book in books:
        if book.author in authors:
            authors[book.author].books[book.title] = book
        else:
            author = Author(author_name=book.author)
            author.books[book.title] = book
            authors[author.author_name] = author

    for author in authors.values():
        for book in author.books.values():
            book.creation_date = book._get_creation_date(book.annotations)
        author.creation_date = author._get_creation_date(author.books)

    return authors


def parse_org(file_str: str) -> Authors:
    root = org_loads(file_str)
    authors: Authors = {}

    for author_node in root.children:
        author = Author.from_org(author_node)

        authors[author.author_name] = author

    return authors


def merge_files(left: Authors, right: Authors) -> Authors:
    results: Authors = {}

    left_names: Set[AuthorName] = set(left.keys())
    right_names: Set[AuthorName] = set(right.keys())

    for author_name in left_names.symmetric_difference(right_names):
        author = left.get(author_name, right[author_name])
        results[author_name] = author

    for author_name in left_names.intersection(right_names):
        # Problem is here.
        left_author: Author = left[author_name]
        right_author: Author = right[author_name]

        left_author.merge(right_author)
        results[author_name] = left_author

    return results


def clean_kindle_string(file_str: str) -> str:
    char_ = r"^Char\\n"
    nid = r"^NID\\n"
    no_char = re.sub(char_, "", file_str)
    return re.sub(nid, "", no_char)


# Notes always come before their highlight
def main(argv):
    try:
        opts, args = getopt.getopt(argv, "hm:k:o:", ["mounted=", "kindle=", "org="])
    except getopt.GetoptError as goe:
        print("kindle_to_org -m <mounted_file> -k <kindle_file> -o <org_file>")
        print(goe)
        sys.exit(2)

    mounted_file, kindle_file, org_file = "", "", ""
    for opt, arg in opts:
        if opt == "-h":
            print("kindle_to_org -m <mounted_file> -k <kindle_file> -o <org_file>")
        elif opt in ("-m", "--mounted"):
            mounted_file = arg
        elif opt in ("-k", "--kindle"):
            kindle_file = arg
            if not kindle_file:
                print("kindle_file is necessary for this script to run")
                sys.exit(2)
        elif opt in ("-o", "--org"):
            org_file = arg
            if not org_file:
                print("kindle_file is necessary for this script to run")
                sys.exit(2)
        else:
            print(f"{opt} is not a valid argument")

    if mounted_file:
        try:
            copyfile(mounted_file, kindle_file)
        except Exception as e:
            print("Copying mounted file failed with exception {e}")
            sys.exit(2)

    try:
        with open(kindle_file, "r") as kf:
            kindle_string = kf.read()
    except Exception as e:
        print(f"Kindle file {kindle_file} was not readable: {e}")
        print("Exiting.")
        sys.exit(2)

    try:
        with open(org_file, "r") as of:
            org_string = of.read()
    except Exception as e:
        print(f"Org file {org_file} not found, writing new one.")
        org_string = ""

    org_data: Authors = parse_org(org_string)
    kindle_data: Authors = parse_kindle(kindle_string)

    merged_data: Authors = merge_files(org_data, kindle_data)

    sorted_merged = sorted([a for a in merged_data.values()])
    output: str = "\n".join([author.to_org() for author in sorted_merged])

    with open(org_file, "w") as ofw:
        ofw.write(output)


if __name__ == "__main__":
    main(sys.argv[1:])
