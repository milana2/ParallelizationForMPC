from collections import defaultdict
from enum import Enum
from typing import Generic, TypeVar, Union, Optional, Protocol
from dataclasses import dataclass, field
from textwrap import indent

import networkx  # type: ignore

from .util import assert_never


class VarVisibility(Enum):
    PLAINTEXT = "plaintext"
    SHARED = "shared"

    def __str__(self) -> str:
        return self.value

    # __repr__ = __str__


class DataType(Enum):
    INT = "int"
    BOOL = "bool"
    TUPLE = "tuple"

    def to_cpp(self, type_env: "TypeEnv", plaintext=True, **kwargs) -> str:
        if self == DataType.INT:
            if plaintext:
                return "std::uint32_t"
            else:
                return "encrypto::motion::SecureUnsignedInteger"
        elif self == DataType.BOOL:
            if plaintext:
                return "bool"
            else:
                return "encrypto::motion::ShareWrapper"
        else:
            raise Exception("Unknown data type")

    def __str__(self) -> str:
        return self.value

    # __repr__ = __str__


@dataclass
class VarType:
    visibility: Optional[VarVisibility] = None
    dims: Optional[list[bool]] = None
    datatype: Optional[DataType] = None
    tuple_types: list["VarType"] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(
            (
                self.visibility,
                self.datatype,
                self.dims,
                tuple(self.tuple_types),
            )
        )

    def drop_dim(self) -> "VarType":
        if self.dims is None:
            return VarType(self.visibility, None, self.datatype)
        else:
            return VarType(self.visibility, self.dims[:-1], self.datatype)

    def add_dim(self) -> "VarType":
        if self.dims is None:
            return VarType(self.visibility, None, self.datatype)
        else:
            return VarType(self.visibility, self.dims + [True], self.datatype)

    def is_plaintext(self) -> bool:
        return self.visibility == VarVisibility.PLAINTEXT

    def is_shared(self) -> bool:
        return self.visibility == VarVisibility.SHARED

    def could_become(self, supertype: "VarType") -> bool:
        return (
            self.visibility in [supertype.visibility, None]
            and self.datatype in [supertype.datatype, None]
            and self.dims in [supertype.dims, None]
            and all(
                t.could_become(subtype)
                for t, subtype in zip(self.tuple_types, supertype.tuple_types)
            )
        )

    def is_complete(self) -> bool:
        return (
            self.visibility is not None
            and self.datatype is not None
            and self.dims is not None
            and (
                self.datatype != DataType.TUPLE
                or all(t.is_complete() for t in self.tuple_types)
            )
        )

    @staticmethod
    def merge(
        *types: "VarType",
        mixed_shared_plaintext_allowed=True,
        mixed_datatypes_allowed=False,
    ) -> "VarType":
        assert len(types) > 0

        # TODO: switch all type errors to syntax errors with the locations of the offending
        # code in the original source code

        merged_type = VarType()

        # Determine the visibility of the merged type
        elem_visibilities = [t.visibility for t in types]
        if (
            len(set(filter(lambda x: x is not None, elem_visibilities))) > 1
            and not mixed_shared_plaintext_allowed
        ):
            raise TypeError(
                "Cannot merge types with different visibilities:\n{}".format(
                    "\n".join(repr(t) for t in types)
                )
            )
        if any(v == VarVisibility.SHARED for v in elem_visibilities):
            merged_type.visibility = VarVisibility.SHARED
        elif all(v == VarVisibility.PLAINTEXT for v in elem_visibilities):
            merged_type.visibility = VarVisibility.PLAINTEXT

        # Determine the dimensionality of the merged type
        elem_dims = [len(t.dims) for t in types if t.dims is not None]
        if len(set(elem_dims)) > 1:
            raise TypeError(
                "Cannot merge types with different dimensionality:\n{}".format(
                    "\n".join(repr(t) for t in types)
                )
            )
        if len(elem_dims) > 0:
            merged_type.dims = [True] * elem_dims[0]

        # Determine the datatype of the merged type
        elem_datatypes = [t.datatype for t in types if t.datatype is not None]
        if len(set(elem_datatypes)) > 1 and not mixed_datatypes_allowed:
            raise TypeError(
                "Cannot merge types with different datatypes:\n{}".format(
                    "\n".join(repr(t) for t in types)
                )
            )
        if len(elem_datatypes) > 0:
            merged_type.datatype = elem_datatypes[0]

        # Determine the tuple types of the merged type
        if len(set(len(t.tuple_types) for t in types)) > 1:
            raise TypeError(
                "Cannot merge types with different tuple types:\n{}".format(
                    "\n".join(repr(t) for t in types)
                )
            )
        tuple_len = len(types[0].tuple_types)
        merged_type.tuple_types = [VarType() for _ in range(tuple_len)]

        elem_tuple_types = [[t.tuple_types[i] for t in types] for i in range(tuple_len)]
        for i in range(tuple_len):
            if len(set(elem_tuple_types[i])) > 1:
                raise TypeError(
                    "Cannot merge types with different tuple types:\n{}".format(
                        "\n".join(repr(t) for t in types)
                    )
                )
            if len(elem_tuple_types[i]) > 0:
                merged_type.tuple_types[i] = elem_tuple_types[i][0]

        return merged_type

    def to_cpp(self, type_env: "TypeEnv", **kwargs) -> str:
        assert self.visibility is not None
        assert self.datatype is not None
        assert self.dims is not None

        if self.datatype == DataType.TUPLE:
            return f"std::tuple<{', '.join(t.to_cpp(type_env, **kwargs) for t in self.tuple_types)}>"
        else:
            str_rep = ""
            for _ in self.dims:
                str_rep += "std::vector<"
            str_rep += self.datatype.to_cpp(
                type_env,
                plaintext=kwargs.get(
                    "plaintext",
                    self.visibility == VarVisibility.PLAINTEXT,
                ),
                **{k: v for k, v in kwargs.items() if k != "plaintext"},
            )
            for _ in self.dims:
                str_rep += ">"
            return str_rep

    def __str__(self) -> str:
        if self.datatype == DataType.TUPLE:
            return "tuple[" + ", ".join(str(t) for t in self.tuple_types) + "]"

        str_rep = f"{self.visibility}["
        if self.dims is not None:
            for _ in self.dims:
                str_rep += "list["
        str_rep += f"{self.datatype}"
        if self.dims is not None:
            for _ in self.dims:
                str_rep += "]"
        str_rep += "]"
        if self.dims is None:
            str_rep += "(unknown dims)"
        return str_rep


PLAINTEXT_INT = VarType(VarVisibility.PLAINTEXT, [], DataType.INT)


@dataclass(frozen=True)
class Var:
    """A variable named `name`"""

    # This is a string for user-provided variables,
    # and an integer for temporary variables the compiler automatically generates
    name: Union[str, int]

    rename_subscript: Optional[int] = None

    def to_cpp(self, type_env: "TypeEnv", plaintext=False, **kwargs) -> str:
        cpp_str = str(self).replace("!", "_")
        if plaintext:
            return f"_MPC_PLAINTEXT_{cpp_str}"
        else:
            return cpp_str

    def __str__(self) -> str:
        name = self.name if isinstance(self.name, str) else f"!{self.name}"
        subscript = "" if self.rename_subscript is None else f"!{self.rename_subscript}"
        return name + subscript


class TypeEnv(defaultdict[Var, VarType]):
    def __str__(self) -> str:
        return "\n".join(
            [
                f"{var}: {var_type}"
                for var, var_type in sorted(self.items(), key=lambda x: str(x[0]))
            ]
        )


@dataclass
class Parameter:
    """A function parameter of the form `var: var_type`"""

    var: Var
    var_type: VarType
    default_values: list[str] = field(
        default_factory=list
    )  # generated from example function calls in the input file
    party_idx: Optional[
        int
    ] = None  # stores the party index associated with this parameter, if it is shared

    def to_cpp(self, type_env: TypeEnv, **kwargs):
        plaintext_kwargs = {k: v for k, v in kwargs.items() if k != "plaintext"}
        if self.var_type.is_shared():
            return (
                self.var_type.to_cpp(type_env, **kwargs)
                + " "
                + self.var.to_cpp(type_env, **plaintext_kwargs)
            )
        else:
            return (
                self.var_type.to_cpp(type_env, plaintext=True, **plaintext_kwargs)
                + " "
                + self.var.to_cpp(type_env, plaintext=True, **plaintext_kwargs)
            )

    def __str__(self) -> str:
        return f"{self.var}: {self.var_type}"


@dataclass(frozen=True)
class Constant:
    """A constant with value `value`"""

    value: Union[int, bool]
    datatype: DataType

    def to_cpp(
        self, type_env: TypeEnv, plaintext=False, as_motion_input=False, **kwargs
    ) -> str:
        if as_motion_input:
            if self.datatype == DataType.INT:
                return f"encrypto::motion::ToInput({self.to_cpp(type_env, plaintext=True, as_motion_input=False)})"
            elif self.datatype == DataType.BOOL:
                return f"encrypto::motion::BitVector(1, {self.to_cpp(type_env, plaintext=True, as_motion_input=False)})"
            else:
                raise NotImplementedError()
        elif plaintext:
            if self.datatype == DataType.INT:
                return f"std::uint32_t({self.value})"
            elif self.datatype == DataType.BOOL:
                return str(self.value).lower()
            else:
                raise NotImplementedError()
        else:
            return f"_MPC_CONSTANT_" + str(self.value).lower()

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, o) -> bool:
        return (
            isinstance(o, Constant)
            and self.value == o.value
            and self.datatype == o.datatype
        )


LoopBound = Union[Var, Constant]


class BinOpKind(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "//"
    LT = "<"
    GT = ">"
    LT_E = "<="
    GT_E = ">="
    EQ = "=="
    NOT_EQ = "!="
    AND = "and"
    OR = "or"
    BIT_AND = "&"
    BIT_OR = "|"
    BIT_XOR = "^"

    def get_ret_datatype(self) -> Optional[DataType]:
        if self in (
            BinOpKind.ADD,
            BinOpKind.SUB,
            BinOpKind.MUL,
            BinOpKind.DIV,
        ):
            return DataType.INT

        elif self in (
            BinOpKind.LT,
            BinOpKind.GT,
            BinOpKind.LT_E,
            BinOpKind.GT_E,
            BinOpKind.EQ,
            BinOpKind.NOT_EQ,
            BinOpKind.AND,
            BinOpKind.OR,
        ):
            return DataType.BOOL

        elif self in (
            BinOpKind.BIT_AND,
            BinOpKind.BIT_XOR,
            BinOpKind.BIT_OR,
        ):
            return None  # return type is the same as the inputs

        else:
            raise ValueError(f"Unhandled binary operation {self}")

    def get_operand_datatypes(self) -> list[DataType]:
        if self in (
            BinOpKind.ADD,
            BinOpKind.SUB,
            BinOpKind.MUL,
            BinOpKind.DIV,
            BinOpKind.LT,
            BinOpKind.GT,
            BinOpKind.LT_E,
            BinOpKind.GT_E,
        ):
            return [DataType.INT]

        elif self in (
            BinOpKind.EQ,
            BinOpKind.NOT_EQ,
            BinOpKind.AND,
            BinOpKind.OR,
            BinOpKind.BIT_AND,
            BinOpKind.BIT_OR,
            BinOpKind.BIT_XOR,
        ):
            return [DataType.INT, DataType.BOOL]

        else:
            raise ValueError(f"Unhandled binary operation {self}")

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        if self == BinOpKind.AND:
            return "&"
        elif self == BinOpKind.OR:
            return "|"
        elif self == BinOpKind.DIV:
            return "/"
        else:
            return str(self)

    def __str__(self) -> str:
        return self.value


class UnaryOpKind(Enum):
    NEGATE = "-"
    NOT = "not"

    def get_ret_datatype(self) -> DataType:
        if self == UnaryOpKind.NEGATE:
            return DataType.INT

        elif self == UnaryOpKind.NOT:
            return DataType.BOOL

        else:
            raise ValueError(f"Unhandled unary operation {self}")

    def get_operand_datatypes(self) -> list[DataType]:
        if self == UnaryOpKind.NEGATE:
            return [DataType.INT]

        elif self == UnaryOpKind.NOT:
            return [DataType.BOOL, DataType.INT]

        else:
            raise ValueError(f"Unhandled unary operation {self}")

    def __str__(self) -> str:
        return self.value


class CppConvertible(Protocol):
    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        ...


OPERAND = TypeVar("OPERAND", bound=CppConvertible)


@dataclass
class BinOp(Generic[OPERAND]):
    """A binary operator expression of the form `left operator right`"""

    left: OPERAND
    operator: BinOpKind
    right: OPERAND

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        # SecureUnsignedIntegers only have operator== and operator> defined on them,
        # so we have to compose all other comparisons manually
        if self.operator == BinOpKind.LT:
            return BinOp(self.right, BinOpKind.GT, self.left).to_cpp(type_env, **kwargs)
        elif self.operator == BinOpKind.NOT_EQ:
            return UnaryOp(
                UnaryOpKind.NOT, BinOp(self.left, BinOpKind.EQ, self.right)
            ).to_cpp(type_env, **kwargs)
        elif self.operator == BinOpKind.LT_E:
            return (
                "("
                + BinOp(self.left, BinOpKind.LT, self.right).to_cpp(type_env, **kwargs)
                + " | "
                + BinOp(self.left, BinOpKind.EQ, self.right).to_cpp(type_env, **kwargs)
                + ")"
            )
        elif self.operator == BinOpKind.GT_E:
            return (
                "("
                + BinOp(self.left, BinOpKind.GT, self.right).to_cpp(type_env, **kwargs)
                + " | "
                + BinOp(self.left, BinOpKind.EQ, self.right).to_cpp(type_env, **kwargs)
                + ")"
            )

        # ShareWrappers don't have operator> defined, so this must always be performed on SecureUnsignedIntegers
        elif self.operator == BinOpKind.GT:
            return f"({self.left.to_cpp(type_env, **kwargs)} {self.operator.to_cpp(type_env, **kwargs)} {self.right.to_cpp(type_env, **kwargs)})"

        # If we're using an arithmetic primitive operation or we're operating on plaintext values,
        # don't cast to a share wrapper
        # Our type analysis should ensure that the only shared values for these operators are
        # SecureUnsignedIntegers, and MOTION does not allow us to use ShareWrappers for them
        elif kwargs.get("plaintext") or self.operator in (
            BinOpKind.ADD,
            BinOpKind.SUB,
            BinOpKind.MUL,
            BinOpKind.DIV,
        ):
            return f"({self.left.to_cpp(type_env, **kwargs)} {self.operator.to_cpp(type_env, **kwargs)} {self.right.to_cpp(type_env, **kwargs)})"

        # Otherwise, convert to sharewrappers since they have more operators defined
        # TODO: go through the operators for ShareWrapper and make sure they're all valid
        # for our protocol
        else:
            return f"(encrypto::motion::ShareWrapper({self.left.to_cpp(type_env, **kwargs)}.Get()) {self.operator.to_cpp(type_env, **kwargs)} encrypto::motion::ShareWrapper({self.right.to_cpp(type_env, **kwargs)}.Get()))"

    def __str__(self) -> str:
        return f"({self.left} {self.operator} {self.right})"

    def __hash__(self) -> int:
        return hash((self.left, self.operator, self.right))


@dataclass
class UnaryOp(Generic[OPERAND]):
    """A unary operator expression of the form `operator operand`"""

    operator: UnaryOpKind
    operand: OPERAND

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        if self.operator == UnaryOpKind.NOT:
            return f"(~{self.operand.to_cpp(type_env, **kwargs)})"
        else:
            # TODO: If negating a SecureUnsignedInteger, change this to a binop where we
            # subtract from _MPC_CONSTANT_0
            return f"({self.operator.value} {self.operand.to_cpp(type_env, **kwargs)})"

    def __str__(self) -> str:
        return f"{self.operator} {self.operand}"

    def __hash__(self) -> int:
        return hash((self.operator, self.operand))


class SubscriptIndexBinOp(BinOp["SubscriptIndex"]):
    pass


class SubscriptIndexUnaryOp(UnaryOp["SubscriptIndex"]):
    pass


SubscriptIndex = Union[Var, Constant, SubscriptIndexBinOp, SubscriptIndexUnaryOp]


def subscript_index_accessed_vars(index: SubscriptIndex) -> list[Var]:
    if isinstance(index, Var):
        return [index]
    elif isinstance(index, Constant):
        return []
    elif isinstance(index, SubscriptIndexBinOp):
        left = subscript_index_accessed_vars(index.left)
        right = subscript_index_accessed_vars(index.right)
        return left + right
    elif isinstance(index, SubscriptIndexUnaryOp):
        return subscript_index_accessed_vars(index.operand)
    else:
        assert_never(index)


@dataclass(frozen=True)
class Subscript:
    """An array subscript expression of the form `array[index]`"""

    array: Var
    index: SubscriptIndex

    def to_cpp(self, type_env: TypeEnv, **kwargs) -> str:
        plaintext_kwargs = {k: v for k, v in kwargs.items() if k != "plaintext"}
        return f"{self.array.to_cpp(type_env, **kwargs)}[{self.index.to_cpp(type_env, plaintext=True, **plaintext_kwargs)}]"

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
    return_type: Optional[VarType]

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
            f"Function {self.name}({parameters})"
            + (f" -> {self.return_type}" if self.return_type is not None else "")
            + ":\n"
            + f"Entry block: {block_indices[self.entry_block]}\n"
            + f"Exit block: {block_indices[self.exit_block]}\n"
            + blocks
            + "\n"
            + f"Edges: {edges}"
        )
