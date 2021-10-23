"""Data types representing a three-address code control flow graph"""

from typing import Union, Optional
from dataclasses import dataclass

import networkx

from ast_shared import *


@dataclass
class BinOp:
    left: Var
    operator: BinOpKind
    right: Var


@dataclass
class UnaryOp:
    operator: UnaryOpKind
    operand: Var


@dataclass
class Index:
    array: Var
    index: Var


AssignLHS = Union[Index, Var]

AssignRHS = Union[Index, Var, BinOp, UnaryOp, ConstantInt]


@dataclass(eq=False)
class Assign:
    lhs: AssignLHS
    rhs: AssignRHS

    def __hash__(self):
        return id(self)


@dataclass
class Jump:
    pass


@dataclass(eq=False)
class ConditionalJump:
    condition: Var

    def __hash__(self):
        return id(self)


@dataclass(eq=False)
class Return:
    value: Var

    def __hash__(self):
        return id(self)


BlockTerminator = Union[Jump, ConditionalJump, Return]


@dataclass(eq=False)
class Block:
    assignments: list[Assign]
    # The block is invalid if it has no terminator.
    # The `Optional` is only for ease of construction.
    terminator: Optional[BlockTerminator]

    # Allow creating graph of blocks
    def __hash__(self):
        return id(self)


BranchKind = Enum("BranchKind", "UNCONDITIONAL TRUE FALSE")


@dataclass
class Function:
    parameters: list[Var]
    body: networkx.DiGraph
    entry_block: Block
    exit_block: Block
