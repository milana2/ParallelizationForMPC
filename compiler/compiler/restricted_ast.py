"""
Data types representing a restricted subset of Python's abstract syntax tree
"""

from typing import Union
from dataclasses import dataclass
from textwrap import indent

from .ast_shared import (
    Var,
    Parameter,
    LoopBound,
    ConstantInt,
    BinOp as _BinOp,
    UnaryOp as _UnaryOp,
    Subscript,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
    BinOpKind,
    UnaryOpKind,
)


Statement = Union["For", "If", "Assign"]


@dataclass
class For:
    """
    A for loop of the form

    ```python
    for counter in range(bound_low, bound_high):
        body
    ```
    """

    counter: Var
    bound_low: LoopBound
    bound_high: LoopBound
    body: list[Statement]

    def __str__(self) -> str:
        body = "\n".join([str(statement) for statement in self.body])
        return (
            f"for {self.counter}: plaintext[int] in range({self.bound_low}, {self.bound_high}):\n"
            + indent(body, "    ")
        )


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

    def __str__(self) -> str:
        then_body = "\n".join(
            [indent(str(statement), "    ") for statement in self.then_body]
        )
        else_body = (
            ""
            if self.else_body == []
            else (
                "\n"
                + f"else:\n"
                + "\n".join(
                    [indent(str(statement), "    ") for statement in self.else_body]
                )
            )
        )
        return f"if {self.condition}:\n" + then_body + else_body


Expression = Union[Var, ConstantInt, "List", "Tuple", "Subscript", "BinOp", "UnaryOp"]


@dataclass
class List:
    """A list expression of the form `[items]` (e.g. `[1, a, b + 2]`)"""

    items: list[Expression]

    def to_cpp(self) -> str:
        # This function only exists to shut mypy up
        raise NotImplementedError("to_cpp() called on restricted ast list")

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"[{items}]"


@dataclass
class Tuple:
    """A tuple expression of the form `(items)` (e.g. `(1, a, b + 2)`)"""

    items: list[Expression]

    def to_cpp(self) -> str:
        # This function only exists to shut mypy up
        raise NotImplementedError("to_cpp() called on restricted ast tuple")

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"({items})"


class BinOp(_BinOp[Expression]):
    pass


class UnaryOp(_UnaryOp[Expression]):
    pass


AssignLHS = Union[Var, Subscript]


@dataclass
class Assign:
    """An assignment statement of the form `lhs = rhs`"""

    lhs: AssignLHS
    rhs: Expression

    def __str__(self) -> str:
        return f"{self.lhs} = {self.rhs}"


@dataclass
class Function:
    """
    A function definition of the form

    ```python
    def name(parameters):
        body
        return return_value
    ```
    """

    name: str
    parameters: list[Parameter]
    body: list[Statement]
    return_value: Expression

    def __str__(self) -> str:
        parameters = ", ".join([str(parameter) for parameter in self.parameters])
        body = "\n".join([str(statement) for statement in self.body]) + "\n"
        return (
            f"def {self.name}({parameters}):\n"
            + indent(body, "    ")
            + f"    return {self.return_value}"
        )
