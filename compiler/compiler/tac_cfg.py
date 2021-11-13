"""Data types representing a three-address code control flow graph"""

from enum import Enum
from typing import Union, Optional
from dataclasses import dataclass

from .ast_shared import (
    Var,
    BinOpKind,
    UnaryOpKind,
    ConstantInt,
    LoopBound,
    CFGFunction as _CFGFunction,
)


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
class Subscript:
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


@dataclass
class Tuple:
    items: list[Var]

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"({items})"


# TODO: Convert ast.IfExp to this?
@dataclass
class Mux:
    condition: Var
    false_value: "AssignLHS"
    true_value: "AssignLHS"

    def __str__(self) -> str:
        return f"MUX({self.condition}, {self.false_value}, {self.true_value})"


AssignLHS = Union[Subscript, Var]

AssignRHS = Union[Subscript, Var, BinOp, UnaryOp, ConstantInt, List, Tuple, Mux]


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


@dataclass
class For:
    counter: Var
    bound_low: LoopBound
    bound_high: LoopBound

    def __str__(self) -> str:
        return f"for {self.counter} in range({self.bound_low}, {self.bound_high})"


@dataclass(eq=False)
class Return:
    value: Var

    def __hash__(self):
        return id(self)

    def __str__(self) -> str:
        return f"return {self.value}"


BlockTerminator = Union[Jump, ConditionalJump, For, Return]


@dataclass(eq=False)
class Block:
    assignments: list[Assign]

    # The block is invalid if it has no terminator.
    # The `Optional` is only for ease of construction.
    terminator: Optional[BlockTerminator]

    # If this node is the merge of the branches of an if-statement,
    # this contains its condition.
    merge_condition: Optional[ConditionalJump]

    # Allow creating graph of blocks
    def __hash__(self):
        return id(self)

    def __str__(self) -> str:
        return (
            (
                ""
                if self.merge_condition is None
                else f"(merge from {self.merge_condition})\n"
            )
            + "\n".join([str(assignment) for assignment in self.assignments])
            + ("" if self.assignments == [] else "\n")
            + str(self.terminator)
        )


class BranchKind(Enum):
    UNCONDITIONAL = "*"
    TRUE = "T"
    FALSE = "F"

    def __str__(self) -> str:
        return self.value


Function = _CFGFunction[Block]
