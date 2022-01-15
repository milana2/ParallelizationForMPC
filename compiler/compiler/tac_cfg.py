"""Data types representing a three-address code control flow graph"""

from enum import Enum
from typing import Union, Optional
from dataclasses import dataclass

from .ast_shared import (
    Var,
    VarType,
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

    def to_cpp(self) -> str:
        # In order to (hopefully) remain more agnostic towards different backend containers,
        # we render tuples and lists using C++'s braced initializer list syntax.
        items = ", ".join(item.to_cpp() for item in self.items)
        return "{" + items + "}"

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"[{items}]"


@dataclass
class Tuple:
    items: list[Atom]

    def to_cpp(self) -> str:
        # In order to (hopefully) remain more agnostic towards different backend containers,
        # we render tuples and lists using C++'s braced initializer list syntax.
        items = ", ".join(item.to_cpp() for item in self.items)
        return "{" + items + "}"

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"({items})"


# TODO: Convert ast.IfExp to this?
@dataclass
class Mux:
    condition: Var
    false_value: Operand
    true_value: Operand

    def to_cpp(self) -> str:
        return f"{self.condition.to_cpp()}.Mux({self.true_value.to_cpp()}, {self.false_value.to_cpp()})"

    def __str__(self) -> str:
        return f"MUX({self.condition}, {self.false_value}, {self.true_value})"


@dataclass
class Update:
    array: Var
    index: SubscriptIndex
    value: Atom

    def to_cpp(self) -> str:
        return f"{self.array}[{self.index.to_cpp()}] = {self.value.to_cpp()}"

    def __str__(self) -> str:
        return f"Update({self.array}, {self.index}, {self.value})"


AssignRHS = Union[Atom, Subscript, BinOp, UnaryOp, List, Tuple, Mux, Update]


@dataclass(eq=False)
class Assign:
    lhs: Var
    rhs: AssignRHS

    def to_cpp(self) -> str:
        if isinstance(self.rhs, Update):
            return (
                self.rhs.to_cpp()
                + "; "
                + (self.lhs.to_cpp() + " = " + self.rhs.array.to_cpp())
                + ";"
            )
            pass
        else:
            return f"{self.lhs.to_cpp()} = {self.rhs.to_cpp()};"

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
