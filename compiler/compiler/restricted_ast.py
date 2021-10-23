"""
Data types representing a restricted subset of Python's abstract syntax tree
"""

from typing import Union
from dataclasses import dataclass

from ast_shared import *


Statement = Union["For", "If", "Assign"]


LoopBound = Union[Var, ConstantInt]


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

    def __str__(self, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        body = "\n".join(
            [statement.__str__(indent_level + 1) for statement in self.body]
        )
        return (
            f"{indent}for {self.counter} in range({self.bound_low}, {self.bound_high}):\n"
            + body
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

    def __str__(self, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        then_body = "\n".join(
            [statement.__str__(indent_level + 1) for statement in self.then_body]
        )
        else_body = (
            ""
            if self.else_body == []
            else "\n"
            + f"{indent}else:\n"
            + "\n".join(
                [statement.__str__(indent_level + 1) for statement in self.else_body]
            )
        )
        return f"{indent}if {self.condition}:\n" + then_body + else_body


Expression = Union[Var, ConstantInt, "Index", "BinOp", "UnaryOp"]


@dataclass(frozen=True)
class Index:
    """An array index expression of the form `array[index]`"""

    array: Var
    index: Expression

    def __str__(self) -> str:
        return f"{self.array}[{self.index}]"


@dataclass
class BinOp:
    """A binary operator expression of the form `left operator right`"""

    left: Expression
    operator: BinOpKind
    right: Expression

    def __str__(self) -> str:
        return f"({self.left} {self.operator} {self.right})"


@dataclass
class UnaryOp:
    """A unary operator expression of the form `operator operand`"""

    operator: UnaryOpKind
    operand: Expression

    def __str__(self) -> str:
        return f"{self.operator} {self.operand}"


AssignLHS = Union[Index, Var]


@dataclass
class Assign:
    """An assignment statement of the form `lhs = rhs`"""

    lhs: AssignLHS
    rhs: Expression

    def __str__(self, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        return f"{indent}{self.lhs} = {self.rhs}"


@dataclass
class Function:
    """
    A function definition of the form

    ```python
    def foo(parameters):
        body
        return return_var
    ```
    """

    parameters: list[Var]
    body: list[Statement]
    return_var: Var

    def __str__(self) -> str:
        parameters = ", ".join([str(parameter) for parameter in self.parameters])
        body = "\n".join([statement.__str__(1) for statement in self.body]) + "\n"
        return f"def foo({parameters}):\n" + body + f"    return {self.return_var}"
