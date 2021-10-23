"""Data types representing code in static single assignment form"""

from typing import Optional
from dataclasses import dataclass
from enum import Enum

import networkx

from ast_shared import *
from tac_cfg import (
    BinOp,
    AssignLHS,
    AssignRHS,
    Assign,
    Jump,
    ConditionalJump,
    Return,
    BlockTerminator,
    BranchKind,
)


@dataclass(eq=False)
class Phi:
    lhs: AssignLHS
    rhs: list[AssignLHS]

    def __hash__(self):
        return id(self)


@dataclass(eq=False)
class Block:
    phi_functions: list[Phi]
    assignments: list[Assign]
    # The block is invalid if it has no terminator.
    # The `Optional` is only for ease of construction.
    terminator: Optional[BlockTerminator]

    # Allow creating graph of blocks
    def __hash__(self):
        return id(self)


@dataclass
class Function:
    parameters: list[Var]
    body: networkx.DiGraph
    entry_block: Block
    exit_block: Block
