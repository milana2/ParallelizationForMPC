from enum import Enum
from typing import Generic, TypeVar, Union, Optional
from dataclasses import dataclass
from textwrap import indent

import networkx  # type: ignore


class VarVisibility(Enum):
    PLAINTEXT = "plaintext"
    SHARED = "shared"


@dataclass(frozen=True)
class VarType:
    visibility: VarVisibility
    dims: int

    def drop_dim(self) -> "VarType":
        return VarType(self.visibility, self.dims - 1)

    def add_dim(self) -> "VarType":
        return VarType(self.visibility, self.dims + 1)

    def is_plaintext(self) -> bool:
        return self.visibility == VarVisibility.PLAINTEXT

    def is_shared(self) -> bool:
        return self.visibility == VarVisibility.SHARED

    def __str__(self) -> str:
        str_rep = f"{self.visibility.value}["
        for _ in range(self.dims):
            str_rep += "list["
        str_rep += "int"
        for _ in range(self.dims):
            str_rep += "]"
        str_rep += "]"
        return str_rep


PLAINTEXT_INT = VarType(VarVisibility.PLAINTEXT, 0)


@dataclass(frozen=True)
class Var:
    """A variable named `name`"""

    name: str

    def __str__(self) -> str:
        return self.name

    def name_without_ssa_rename(self) -> str:
        return self.name.strip("!")[0]


@dataclass
class Parameter:
    """A function parameter of the form `var: var_type`"""

    var: Var
    var_type: VarType

    def __str__(self) -> str:
        return f"{self.var}: {self.var_type}"


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
    LT = "<"
    GT = ">"
    LT_E = "<="
    GT_E = ">="
    EQ = "=="
    NOT_EQ = "!="
    AND = "and"
    OR = "or"

    def __str__(self) -> str:
        return self.value


class UnaryOpKind(Enum):
    NEGATE = "-"
    NOT = "not"

    def __str__(self) -> str:
        return self.value


OPERAND = TypeVar("OPERAND")


@dataclass
class BinOp(Generic[OPERAND]):
    """A binary operator expression of the form `left operator right`"""

    left: OPERAND
    operator: BinOpKind
    right: OPERAND

    def __str__(self) -> str:
        return f"({self.left} {self.operator} {self.right})"


@dataclass
class UnaryOp(Generic[OPERAND]):
    """A unary operator expression of the form `operator operand`"""

    operator: UnaryOpKind
    operand: OPERAND

    def __str__(self) -> str:
        return f"{self.operator} {self.operand}"


class SubscriptIndexBinOp(BinOp["SubscriptIndex"]):
    pass


class SubscriptIndexUnaryOp(UnaryOp["SubscriptIndex"]):
    pass


SubscriptIndex = Union[Var, ConstantInt, SubscriptIndexBinOp, SubscriptIndexUnaryOp]


@dataclass(frozen=True)
class Subscript:
    """An array subscript expression of the form `array[index]`"""

    array: Var
    index: SubscriptIndex

    def __hash__(self) -> int:
        return id(self)

    def __str__(self) -> str:
        return f"{self.array}[{self.index}]"


BLOCK = TypeVar("BLOCK")


@dataclass
class CFGFunction(Generic[BLOCK]):
    name: str
    parameters: list[Parameter]
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
            f"Function {self.name}({parameters}):\n"
            + f"Entry block: {block_indices[self.entry_block]}\n"
            + f"Exit block: {block_indices[self.exit_block]}\n"
            + blocks
            + "\n"
            + f"Edges: {edges}"
        )
