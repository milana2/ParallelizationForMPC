from dataclasses import dataclass
from typing import Union, Optional, cast, TypeVar
from textwrap import indent

from .ssa import (
    Atom,
    Operand,
    Var,
    Phi,
    Assign,
    LoopBound,
    AssignLHS,
    AssignRHS,
    Constant,
    Subscript,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
    BinOp,
    UnaryOp,
    List,
    Tuple,
    Mux,
    Update,
    VectorizedUpdate,
    assign_rhs_accessed_vars,
)
from .tac_cfg import LiftExpr, DropDim
from .ast_shared import (
    VarType,
    BinOpKind,
    Parameter,
    UnaryOpKind,
    TypeEnv,
    VectorizedAccess,
)
from .util import assert_never

Statement = Union[Phi, Assign, "For", "Return"]


@dataclass(frozen=True)
class For:
    counter: Var
    bound_low: LoopBound
    bound_high: LoopBound
    body: list[Statement]
    is_monolithic: bool = False

    def __hash__(self):
        return id(self)

    def heading_str(self) -> str:
        return (
            f"for {self.counter} in range({self.bound_low}, {self.bound_high}):"
            + " (monolithic)" * self.is_monolithic
        )

    def __str__(self) -> str:
        body = "\n".join([str(statement) for statement in self.body])
        return self.heading_str() + "\n" + indent(body, "    ")

    # needed for dependency graph
    @property
    def lhs(self) -> Var:
        return self.counter


@dataclass(frozen=True)
class Return:
    value: Var

    def __str__(self) -> str:
        return f"return {self.value}"


@dataclass
class Function:
    name: str
    parameters: list[Parameter]
    body: list[Statement]
    return_type: Optional[VarType]

    def __str__(self) -> str:
        parameters = ", ".join([str(parameter) for parameter in self.parameters])
        body = "\n".join([str(statement) for statement in self.body])
        return (
            f"def {self.name}({parameters})"
            + (f" -> {self.return_type}" if self.return_type is not None else "")
            + ":\n"
            + indent(body, "    ")
        )
