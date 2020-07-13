#!/usr/bin/env ipython

from typing import Tuple, Union, Optional, Dict, Any


KINDLE_SEPARATOR: str = "=========="
EMACS_TIME = "[%Y-%m-%d %a %H:%M]"
EMACS_DATE = "<%Y-%m-%d %a>"
KINDLE_TIME = "Added on %A, %B %d, %Y %I:%M:%S %p"


# Type definitions
PageRange = Tuple[Union[str, int], Optional[Union[str, int]]]
LocationRange = Tuple[int, Optional[int]]
Hash = int
Heading = str
BookTitle = str
AuthorName = str
Series = str
IsNoteCollated = bool
Properties = Dict[str, Any]
