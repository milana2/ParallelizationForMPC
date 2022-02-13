from dataclasses import dataclass
from typing import Union, Optional
from textwrap import indent

from .ssa import (
    Atom,
    Operand,
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
    assign_rhs_accessed_vars,
)
from .ast_shared import VarType, BinOpKind, Parameter, UnaryOpKind, TypeEnv


@dataclass(frozen=True)
class DropDim:
    lhs: Var
    input_arr: Var

    def __str__(self) -> str:
        return f"{self.lhs} = drop_dim({self.input_arr})"

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        raise NotImplementedError()


@dataclass(frozen=True)
class RaiseDim:
    lhs: Var
    input_arr: Var
    access_pattern: Optional[SubscriptIndex]
    dims: tuple[tuple[Var, LoopBound], ...]

    def __str__(self) -> str:
        dims = ",".join([f"{var}:{bound}" for var, bound in self.dims])
        dims = f"({dims})"
        if self.access_pattern is None:
            return f"{self.lhs} = raise_dim({self.input_arr}, {dims})"
        else:
            return f"{self.lhs} = raise_dim({self.input_arr}, {self.access_pattern}, {dims})"

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        raise NotImplementedError()


Statement = Union[Phi, Assign, "For", RaiseDim, DropDim]


@dataclass(frozen=True)
class For:
    counter: Var
    bound_low: LoopBound
    bound_high: LoopBound
    body: list[Statement]

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        # Pseudo-phi nodes are implemented by first initializing the variable before entering the loop,
        # then updating the variable's value at the end of each loop.
        phi_initializations = "// Initialize phi values\n" + "\n".join(
            phi.lhs.to_cpp(type_env, **kwargs)
            + " = "
            + phi.rhs_false.to_cpp(type_env, **kwargs)
            + ";"
            for phi in self.body
            if isinstance(phi, Phi)
        )

        plaintext_kwargs = {k: v for k, v in kwargs.items() if k != "plaintext"}

        header = f"for ({self.counter.to_cpp(type_env, plaintext=True, **plaintext_kwargs)} = {self.bound_low.to_cpp(type_env, plaintext=True, **plaintext_kwargs)}; {self.counter.to_cpp(type_env, plaintext=True, **plaintext_kwargs)} < {self.bound_high.to_cpp(type_env, plaintext=True, **plaintext_kwargs)}; {self.counter.to_cpp(type_env, plaintext=True, **plaintext_kwargs)}++) {{"
        body = (
            "\n".join(
                stmt.to_cpp(type_env, **kwargs)
                for stmt in self.body
                if not isinstance(stmt, Phi)
            )
            + "\n"
        )
        phi_updates = "// Update phi values\n" + "\n".join(
            phi.lhs.to_cpp(type_env, **kwargs)
            + " = "
            + phi.rhs_true.to_cpp(type_env, **kwargs)
            + ";"
            for phi in self.body
            if isinstance(phi, Phi)
        )

        return (
            "\n"
            + phi_initializations
            + "\n"
            + header
            + "\n"
            # Initialize loop counter for use in loop
            + f"    {self.counter.to_cpp(type_env, **kwargs)} = party->In<Protocol>(encrypto::motion::ToInput({self.counter.to_cpp(type_env, plaintext=True, **plaintext_kwargs)}), 0);"
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
