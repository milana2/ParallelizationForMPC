"""
Data types representing a restricted subset of Python's abstract syntax tree
"""

from typing import Union
from dataclasses import dataclass

from ast_shared import *


Statement = Union["For", "If", "Assign", "Return"]


LoopBound = Union[Var, ConstantInt]


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

    condition: "Expression"
    then_body: list[Statement]
    else_body: list[Statement]


Expression = Union[Var, ConstantInt, "Index", "BinOp", "UnaryOp"]


@dataclass(frozen=True)
class Index:
    """An array index expression of the form `array[index]`"""

    array: Var
    index: Expression


@dataclass
class BinOp:
    """A binary operator expression of the form `left operator right`"""

    left: Expression
    operator: BinOpKind
    right: Expression


@dataclass
class UnaryOp:
    """A unary operator expression of the form `operator operand`"""

    operator: UnaryOpKind
    operand: Expression


AssignLHS = Union[Index, Var]


@dataclass
class Assign:
    """An assignment statement of the form `lhs = rhs`"""

    lhs: AssignLHS
    rhs: Expression


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
