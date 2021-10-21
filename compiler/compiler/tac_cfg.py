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


AssignLHS = Union[Subscript, Var]

AssignRHS = Union[Subscript, Var, BinOp, ConstantInt]


@dataclass
class Assign:
    lhs: AssignLHS
    rhs: AssignRHS


@dataclass
class Jump:
    pass


@dataclass
class ConditionalJump:
    condition: Var


@dataclass
class Return:
    value: Var


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
