"""Data types representing code in static single assignment form"""

from typing import Optional
from dataclasses import dataclass

from .ast_shared import Var, ConstantInt
from .ast_shared import CFGFunction as _CFGFunction
from .tac_cfg import (
    BinOp,
    UnaryOp,
    AssignLHS,
    AssignRHS,
    Index,
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

    def __str__(self) -> str:
        rhs = ", ".join([str(v) for v in self.rhs])
        return f"{self.lhs} = Φ({rhs})"


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

    def __str__(self) -> str:
        return (
            "\n".join([str(phi) for phi in self.phi_functions])
            + ("" if self.phi_functions == [] else "\n")
            + "\n".join([str(assignment) for assignment in self.assignments])
            + ("" if self.assignments == [] else "\n")
            + str(self.terminator)
        )


Function = _CFGFunction[Block]
