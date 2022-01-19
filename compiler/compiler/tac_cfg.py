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

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        # In order to (hopefully) remain more agnostic towards different backend containers,
        # we render tuples and lists using C++'s braced initializer list syntax.
        items = ", ".join(item.to_cpp(type_env, **kwargs) for item in self.items)
        return "{" + items + "}"

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"[{items}]"


@dataclass
class Tuple:
    items: list[Atom]

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        items = ", ".join(item.to_cpp(type_env, **kwargs) for item in self.items)
        return "std::make_tuple(" + items + ")"

    def __str__(self) -> str:
        items = ", ".join([str(item) for item in self.items])
        return f"({items})"


# TODO: Convert ast.IfExp to this?
@dataclass
class Mux:
    condition: Var
    false_value: Operand
    true_value: Operand

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        if isinstance(self.true_value, Var):
            true_shared = type_env[self.true_value].is_shared()
        elif isinstance(self.true_value, Constant):
            true_shared = False
        else:
            true_shared = type_env[self.true_value.array].is_shared()

        if isinstance(self.false_value, Var):
            false_shared = type_env[self.false_value].is_shared()
        elif isinstance(self.false_value, Constant):
            false_shared = False
        else:
            false_shared = type_env[self.false_value.array].is_shared()

        true_cpp_str = self.true_value.to_cpp(type_env, **kwargs) + ".Get()"
        false_cpp_str = self.false_value.to_cpp(type_env, **kwargs) + ".Get()"

        return f"{self.condition.to_cpp(type_env, **kwargs)}.Mux({true_cpp_str}, {false_cpp_str})"

    def __str__(self) -> str:
        return f"MUX({self.condition}, {self.false_value}, {self.true_value})"


@dataclass
class Update:
    array: Var
    index: SubscriptIndex
    value: Atom

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        plaintext_kwargs = {k: v for k, v in kwargs.items() if k != "plaintext"}
        return f"{self.array.to_cpp(type_env, **kwargs)};\n{self.array.to_cpp(type_env, **kwargs)}[{self.index.to_cpp(type_env, plaintext=True, **plaintext_kwargs)}] = {self.value.to_cpp(type_env, **kwargs)}"

    def __str__(self) -> str:
        return f"Update({self.array}, {self.index}, {self.value})"


AssignRHS = Union[Atom, Subscript, BinOp, UnaryOp, List, Tuple, Mux, Update]


@dataclass(eq=False)
class Assign:
    lhs: Var
    rhs: AssignRHS

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        shared_assignment = (
            self.lhs.to_cpp(type_env, **kwargs)
            + " = "
            + self.rhs.to_cpp(type_env, **kwargs)
            + ";"
        )

        plaintext_kwargs = {k: v for k, v in kwargs.items() if k != "plaintext"}
        plaintext_assignment = (
            self.lhs.to_cpp(type_env, plaintext=True, **plaintext_kwargs)
            + " = "
            + self.rhs.to_cpp(type_env, plaintext=True, **plaintext_kwargs)
            + ";"
        )

        if (
            type_env[self.lhs].is_shared()
            or type_env[self.lhs].datatype == DataType.TUPLE
        ):
            return shared_assignment
        else:
            return shared_assignment + "\n" + plaintext_assignment

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
