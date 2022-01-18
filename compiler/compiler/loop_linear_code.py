from dataclasses import dataclass
from typing import Union, Optional
from textwrap import indent

from .ssa import (
    Var,
    Phi,
    Assign,
    LoopBound,
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
)
from .ast_shared import VarType, BinOpKind, Parameter, UnaryOpKind, TypeEnv


Statement = Union[Phi, Assign, "For"]


@dataclass(frozen=True)
class For:
    counter: Var
    bound_low: LoopBound
    bound_high: LoopBound
    body: list[Statement]

    def to_cpp(self, type_env: TypeEnv) -> str:
        # Pseudo-phi nodes are implemented by first initializing the variable before entering the loop,
        # then updating the variable's value at the end of each loop.
        phi_initializations = "// Initialize phi values\n" + "\n".join(
            phi.lhs.to_cpp()
            + " = party->In<Protocol>(encrypto::motion::ToInput("
            + phi.rhs_false.to_cpp()
            + "), 0);"
            for phi in self.body
            if isinstance(phi, Phi)
        )

        header = f"for ({self.counter.to_cpp()} = {self.bound_low.to_cpp()}; {self.counter.to_cpp()} < {self.bound_high.to_cpp()}; {self.counter.to_cpp()}++) {{"
        body = (
            "\n".join(stmt.to_cpp() for stmt in self.body if not isinstance(stmt, Phi))
            + "\n"
        )
        phi_updates = "// Update phi values\n" + "\n".join(
            phi.lhs.to_cpp() + " = " + phi.rhs_true.to_cpp() + ";"
            for phi in self.body
            if isinstance(phi, Phi)
        )

        return (
            "\n"
            + phi_initializations
            + "\n"
            + header
            + "\n"
            + indent(body, "    ")
            + "\n"
            + indent(phi_updates, "    ")
            + "\n}\n"
        )

    def __hash__(self):
        return id(self)

    def heading_str(self) -> str:
        return f"for {self.counter} in range({self.bound_low}, {self.bound_high}):"

    def __str__(self) -> str:
        body = "\n".join([str(statement) for statement in self.body])
        return self.heading_str() + "\n" + indent(body, "    ")


@dataclass
class Function:
    name: str
    parameters: list[Parameter]
    body: list[Statement]
    return_value: Var
    return_type: Optional[VarType]

    def __str__(self) -> str:
        parameters = ", ".join([str(parameter) for parameter in self.parameters])
        body = "\n".join([str(statement) for statement in self.body]) + "\n"
        return (
            f"def {self.name}({parameters})"
            + (f" -> {self.return_type}" if self.return_type is not None else "")
            + ":\n"
            + indent(body, "    ")
            + f"    return {self.return_value}"
        )
