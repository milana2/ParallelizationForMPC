"""Data types representing three-address code"""

from typing import Union
from dataclasses import dataclass
from enum import Enum


@dataclass
class Var:
    """A variable named `name`"""

    name: str


@dataclass
class ConstantInt:
    """A constant integer with value `value`"""

    value: int


Statement = Union["For", "If", "Assign", "Return"]


LoopBound = Union[Var, int]


@dataclass
class For:
    """
    A for loop of the form

    ```python
    for counter in range(bound):
        body
    ```
    """

    counter: Var
    bound: LoopBound
    body: list[Statement]


@dataclass
class If:
    """
    An if statement of the form

    ```python
    if condition:
        then_body
    else:
        else_body
    ```

    If there is no `else` block, then `else_body` is an empty list.
    """

    condition: Var
    then_body: list[Statement]
    else_body: list[Statement]


Expression = Union["Subscript", "BinOp"]


@dataclass
class Subscript:
    """An array subscript expression of the form `array[index]`"""

    array: Var
    index: Var


BinOpLHS = Union[Subscript, Var]

BinOpKind = Enum("BinOpKind", "ADD SUB MUL DIV MOD SHL SHR")

BinOpRHS = Union[Subscript, Var, ConstantInt]


@dataclass
class BinOp:
    """A binary operator expression of the form `left operator right`"""

    left: BinOpLHS
    operator: BinOpKind
    right: BinOpRHS


AssignLHS = Union[Subscript, Var]

AssignRHS = Union[Subscript, Var, BinOp]


@dataclass
class Assign:
    """An assignment statement of the form `lhs = rhs`"""

    lhs: AssignLHS
    rhs: AssignRHS


@dataclass
class Return:
    """A return statement of the form `return value`"""

    value: Var


@dataclass
class Function:
    """
    A function definition of the form

    ```python
    def foo(parameters):
        body
    ```
    """

    parameters: list[Var]
    body: list[Statement]
