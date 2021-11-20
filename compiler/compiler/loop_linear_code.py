from dataclasses import dataclass
from typing import Union
from textwrap import indent

from .ssa import (
    Var,
    Phi,
    Assign,
    LoopBound,
    AssignRHS,
    ConstantInt,
    Subscript,
    BinOp,
    UnaryOp,
    List,
    Tuple,
    Mux,
    Update,
    UpdateValue,
)


Statement = Union[Phi, Assign, "For"]


@dataclass(frozen=True)
class For:
    counter: Var
    bound_low: LoopBound
    bound_high: LoopBound
    body: list[Statement]

    def __hash__(self):
        return id(self)

    def heading_str(self) -> str:
        return f"for {self.counter} in range({self.bound_low}, {self.bound_high}):"

    def __str__(self) -> str:
        body = "\n".join([str(statement) for statement in self.body])
        return self.heading_str() + "\n" + indent(body, "    ")


@dataclass
class Function:
    parameters: list[Var]
    body: list[Statement]
    return_value: Var

    def __str__(self) -> str:
        parameters = ", ".join([str(parameter) for parameter in self.parameters])
        body = "\n".join([str(statement) for statement in self.body]) + "\n"
        return (
            f"def foo({parameters}):\n"
            + indent(body, "    ")
            + f"    return {self.return_value}"
        )
