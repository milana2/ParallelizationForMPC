from dataclasses import dataclass
from typing import Union
from textwrap import indent

from .ssa import Var, Phi, Assign, LoopBound


Statement = Union[Phi, Assign, "For"]


@dataclass
class For:
    counter: Var
    bound_low: LoopBound
    bound_high: LoopBound
    body: list[Statement]

    def __str__(self) -> str:
        body = "\n".join([str(statement) for statement in self.body])
        return (
            f"for {self.counter} in range({self.bound_low}, {self.bound_high}):\n"
            + indent(body, "    ")
        )


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