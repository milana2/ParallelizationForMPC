"""Data types representing a three-address code control flow graph"""

from enum import Enum
from lib2to3.pgen2.token import OP
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
    VectorizedAccess,
    subscript_index_accessed_vars,
)
from .util import assert_never


Atom = Union[Var, Constant]

Operand = Union[Atom, Subscript, "BinOp", "UnaryOp", VectorizedAccess]


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


AssignRHS = Union[
    Atom,
    Subscript,
    BinOp,
    UnaryOp,
    List,
    Tuple,
    Mux,
    Update,
    "LiftExpr",
    "DropDim",
    VectorizedAccess,
]


@dataclass(frozen=True)
class DropDim:
    array: Var
    dims: tuple[LoopBound, ...]

    def __str__(self) -> str:
        return f"drop_dim({self.array})"


@dataclass(frozen=True)
class LiftExpr:
    expr: AssignRHS
    dims: tuple[tuple[Var, LoopBound], ...]

    def __str__(self) -> str:
        dims = ", ".join([f"{var}:{bound}" for var, bound in self.dims])
        return f"lift({self.expr}, ({dims}))"


def assign_rhs_accessed_vars(rhs: AssignRHS) -> list[Var]:
    if isinstance(rhs, Var):
        return [rhs]
    elif isinstance(rhs, Constant):
        return []
    elif isinstance(rhs, Subscript):
        return [rhs.array] + subscript_index_accessed_vars(rhs.index)
    elif isinstance(rhs, VectorizedAccess):
        return [rhs.array] + list(
            counter
            for counter, vectorized in zip(rhs.idx_vars, rhs.vectorized_dims)
            if not vectorized
        )
    elif isinstance(rhs, BinOp):
        return assign_rhs_accessed_vars(rhs.left) + assign_rhs_accessed_vars(rhs.right)
    elif isinstance(rhs, UnaryOp):
        return assign_rhs_accessed_vars(rhs.operand)
    elif isinstance(rhs, (List, Tuple)):
        return [var for item in rhs.items for var in assign_rhs_accessed_vars(item)]
    elif isinstance(rhs, Mux):
        return (
            assign_rhs_accessed_vars(rhs.condition)
            + assign_rhs_accessed_vars(rhs.false_value)
            + assign_rhs_accessed_vars(rhs.true_value)
        )
    elif isinstance(rhs, Update):
        return (
            [rhs.array]
            + subscript_index_accessed_vars(rhs.index)
            + assign_rhs_accessed_vars(rhs.value)
        )
    elif isinstance(rhs, LiftExpr):
        return assign_rhs_accessed_vars(rhs.expr)
    elif isinstance(rhs, DropDim):
        return [rhs.array]
    else:
        assert_never(rhs)


@dataclass(eq=False)
class Assign:
    lhs: Union[Var, VectorizedAccess]
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
