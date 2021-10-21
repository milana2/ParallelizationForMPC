from enum import Enum
from dataclasses import dataclass


@dataclass(frozen=True)
class Var:
    """A variable named `name`"""

    name: str


@dataclass(frozen=True)
class ConstantInt:
    """A constant integer with value `value`"""

    value: int


@dataclass(frozen=True)
class Subscript:
    """An array subscript expression of the form `array[index]`"""

    array: Var
    index: Var


BinOpKind = Enum("BinOpKind", "ADD SUB MUL DIV MOD SHL SHR LESS_THAN")
