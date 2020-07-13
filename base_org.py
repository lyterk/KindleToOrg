#!/usr/bin/env python3

import re

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from orgparse.node import OrgNode
from typing import Type, TypeVar, Optional, List, Dict, Any, Set, Tuple

from static import EMACS_DATE, KINDLE_TIME, EMACS_TIME
from utility_functions import head


Y = TypeVar("Y", bound="EmacsDateTime")


class EmacsDateTime(datetime):
    def __str__(self) -> str:
        return self.strftime(EMACS_TIME)

    @classmethod
    def kindle_strptime(cls: Type[Y], s: str) -> Y:
        return cls.strptime(s, KINDLE_TIME)

    @classmethod
    def org_strptime(cls: Type[Y], s: str) -> Optional[Y]:
        return cls.strptime(s, EMACS_TIME) if s else None


Z = TypeVar("Z", bound="EmacsDate")


class EmacsDate(date):
    def __str__(self) -> str:
        return self.strftime(EMACS_DATE)

    @classmethod
    def org_strptime(cls: Type[Z], s: str) -> Z:
        return cls.strptime(s, EMACS_DATE)


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


# Exceptions
class OrgHeaderException(Exception):
    pass


class OrgTime(Enum):
    Scheduled: EmacsDate
    Closed: EmacsDateTime
    Deadline: EmacsDate


@dataclass
class Progress:
    num: int = 0
    denom: int = 0

    def __str__(self) -> str:
        return f"[{self.num}/{self.denom}]"


W = TypeVar("W", bound="BaseOrg")


@dataclass
class BaseOrg:
    heading: str = ""
    status: Optional[Todo] = None
    body: Optional[str] = None
    org_time: Optional[OrgTime] = None
    creation_date: Optional[EmacsDateTime] = None
    level: int = 0
    progress: Progress = Progress(num=0, denom=0)
    show_progress: bool = False
    important_times: List[OrgTime] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

    def __str__(self) -> str:
        gapped_status = " " + self.status.value if self.status else ""
        gapped_progress = (
            " " + str(self.progress) if self.progress and self.show_progress else ""
        )
        body = "\n" + self.body if self.body else ""
        first_line = (
            f"""{'*' * self.level}{gapped_status} {self.heading}{gapped_progress}"""
        )
        return first_line + "\n" + self.write_properties() + body

    @classmethod
    def parse_heading(cls: Type[W], node: OrgNode) -> Tuple[Todo, str]:
        def check_match(s: str) -> Todo:
            if s == " ":
                return Todo.Unchecked
            elif s == "X":
                return Todo.Checked
            elif s == "?":
                return Todo.CheckWait
            elif s == "-":
                return Todo.CheckStart
            raise OrgHeaderException(f"Invalid check value: {s}")

        result_heading: str = node.heading.strip()

        check_rex = r"\[( |X|\?|-)\]"
        try:
            checkbox = head(
                list(map(check_match, re.findall(check_rex, result_heading)))
            )
        except ValueError as ve:
            raise OrgHeaderException(ve.args[0])
        if node.todo:
            status = Todo(node.todo)
        elif checkbox:
            status = checkbox

            result_heading = result_heading[4:].strip()

        # Collect and ignore whatever is in the progress boxes (e.g. [1/2], [/])
        progress_rex = r"\[((\d)+)?\/((\d)+)?\]"
        progress = re.search(progress_rex, result_heading)
        if progress:
            result_heading = result_heading[0 : progress.span()[0] - 1].strip()

        return status, result_heading

    def write_properties(self) -> str:
        """Write properties out in alphanumeric order for determinism."""
        props_sorted = sorted(
            [(key, value) for key, value in self.properties.items() if value],
            key=lambda kv: kv[0],
        )
        if len(props_sorted) > 0:
            props = (
                "\n" + "\n".join([f":{k.upper()}: {v}" for k, v in props_sorted]) + "\n"
            )
        else:
            props = "\n"
        return f":PROPERTIES:{props}:END:"

    @classmethod
    def from_node(
        org_node: OrgNode, expected_props: Set[str]
    ) -> Tuple[W, Dict[str, Any]]:
        all_props = org_node.properties
        others = Dict[str, Any] = {}
        for prop_key, prop in all_props.items():
            del all_props[prop_key]
            if prop_key in expected_props:
                others[prop_key.lower()] = prop
            else:
                all_props[prop_key.lower()] = prop

    def _org_merge(self, other: W) -> None:
        self_todo, other_todo = self.status or Todo.NoTodo, other.status or Todo.NoTodo
        final_status = self_todo._merge(other_todo)

        sbody, obody = self.body or "", other.body or ""
        if sbody.strip() == obody.strip():
            final_body: str = sbody.strip()
        else:
            final_body = sbody.strip() + obody.strip()

        final_props = {**self.properties, **other.properties}
        self.status = final_status
        self.body = final_body
        self.properties = final_props
