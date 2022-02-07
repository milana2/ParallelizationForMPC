"""Data types representing a three-address code control flow graph"""

from enum import Enum
from typing import Union, Optional
from dataclasses import dataclass

from .ast_shared import (
    Var,
    VarType,
    DataType,
    Parameter,
    BinOpKind,
    UnaryOpKind,
    Constant,
    LoopBound,
    Subscript,
    SubscriptIndex,
    CFGFunction as _CFGFunction,
    BinOp as _BinOp,
    UnaryOp as _UnaryOp,
    TypeEnv,
)


Atom = Union[Var, Constant]

Operand = Union[Atom, Subscript]


class BinOp(_BinOp[Operand]):
    pass


class UnaryOp(_UnaryOp[Operand]):
    pass


@dataclass
class List:
    items: list[Atom]

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"[{items}]"


@dataclass
class Tuple:
    items: list[Atom]

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"({items})"


# TODO: Convert ast.IfExp to this?
@dataclass
class Mux:
    condition: Var
    false_value: Operand
    true_value: Operand

    def __str__(self) -> str:
        return f"MUX({self.condition}, {self.false_value}, {self.true_value})"


@dataclass
class Update:
    array: Var
    index: SubscriptIndex
    value: Atom

    def __str__(self) -> str:
        return f"Update({self.array}, {self.index}, {self.value})"


AssignRHS = Union[Atom, Subscript, BinOp, UnaryOp, List, Tuple, Mux, Update]


@dataclass(eq=False)
class Assign:
    lhs: Var
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

    def __hash__(self):
        return id(self)

    def __str__(self) -> str:
        return f"for {self.counter}: plaintext[int] in range({self.bound_low}, {self.bound_high})"

    @property
    def lhs(self) -> Var:
        return self.counter

    @lhs.setter
    def lhs(self, lhs: Var) -> None:
        self.counter = lhs


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
