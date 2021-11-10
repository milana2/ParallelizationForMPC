from enum import Enum
from typing import Generic, TypeVar, Union
from dataclasses import dataclass
from textwrap import indent

import networkx


@dataclass(frozen=True)
class Var:
    """A variable named `name`"""

    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class ConstantInt:
    """A constant integer with value `value`"""

    value: int

    def __str__(self) -> str:
        return str(self.value)


LoopBound = Union[Var, ConstantInt]


class BinOpKind(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "//"
    MOD = "%"
    SHL = "<<"
    SHR = ">>"
    LESS_THAN = "<"
    GREATER_THAN = ">"
    EQUALS = "=="
    AND = "and"
    OR = "or"

    def __str__(self) -> str:
        return self.value


class UnaryOpKind(Enum):
    NEGATE = "-"
    NOT = "not"

    def __str__(self) -> str:
        return self.value


BLOCK = TypeVar("BLOCK")


@dataclass
class CFGFunction(Generic[BLOCK]):
    parameters: list[Var]
    body: networkx.DiGraph
    entry_block: BLOCK
    exit_block: BLOCK

    def __str__(self) -> str:
        parameters = ", ".join([str(parameter) for parameter in self.parameters])
        block_indices = {block: i for i, block in enumerate(self.body.nodes)}
        blocks = "\n".join(
            [
                f"Block {i}:\n{indent(str(block), '    ')}"
                for i, block in enumerate(self.body.nodes)
            ]
        )
        edges = " ".join(
            [
                f"({block_indices[u]}, {block_indices[v]}, {label})"
                for u, v, label in self.body.edges(data="label")
            ]
        )
        return (
            f"Function({parameters}):\n"
            + f"Entry block: {block_indices[self.entry_block]}\n"
            + f"Exit block: {block_indices[self.exit_block]}\n"
            + blocks
            + "\n"
            + f"Edges: {edges}"
        )
