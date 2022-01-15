# This file is not a benchmark, but provides necessary types and functions for programs using our compiler

from typing import TypeVar, Generic

_T = TypeVar("_T")


class shared(Generic[_T]):
    pass
