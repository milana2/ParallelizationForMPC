"""Data types representing a three-address code control flow graph"""

from enum import Enum
from typing import Union, Optional
from dataclasses import dataclass

from .ast_shared import Var, BinOpKind, UnaryOpKind, ConstantInt
from .ast_shared import CFGFunction as _CFGFunction


@dataclass
class BinOp:
    left: Var
    operator: BinOpKind
    right: Var

    def __str__(self) -> str:
        return f"{self.left} {self.operator} {self.right}"


@dataclass
class UnaryOp:
    operator: UnaryOpKind
    operand: Var

    def __str__(self) -> str:
        return f"{self.operator} {self.operand}"


@dataclass(frozen=True)
class Index:
    array: Var
    index: Var

    def __str__(self) -> str:
        return f"{self.array}[{self.index}]"


@dataclass
class List:
    items: list[Var]

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"[{items}]"


AssignLHS = Union[Index, Var]

AssignRHS = Union[Index, Var, BinOp, UnaryOp, ConstantInt, List]


@dataclass(eq=False)
class Assign:
    lhs: AssignLHS
    rhs: AssignRHS

    def __hash__(self):
        return id(self)

    def __str__(self) -> str:
        return f"{self.lhs} = {self.rhs}"


@dataclass
class Jump:
    def __str__(self) -> str:
        return "jump"


@dataclass(eq=False)
class ConditionalJump:
    condition: Var

    def __hash__(self):
        return id(self)

    def __str__(self) -> str:
        return f"conditional jump {self.condition}"


@dataclass(eq=False)
class Return:
    value: Var

    def __hash__(self):
        return id(self)

    def __str__(self) -> str:
        return f"return {self.value}"


BlockTerminator = Union[Jump, ConditionalJump, Return]


@dataclass(eq=False)
class Block:
    assignments: list[Assign]
    # The block is invalid if it has no terminator.
    # The `Optional` is only for ease of construction.
    terminator: Optional[BlockTerminator]

    # Allow creating graph of blocks
    def __hash__(self):
        return id(self)

    def __str__(self) -> str:
        return (
            "\n".join([str(assignment) for assignment in self.assignments])
            + ("" if self.assignments == [] else "\n")
            + str(self.terminator)
        )


BranchKind = Enum("BranchKind", "UNCONDITIONAL TRUE FALSE")


Function = _CFGFunction[Block]
