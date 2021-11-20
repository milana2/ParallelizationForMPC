"""Data types representing code in static single assignment form"""

import networkx
from dataclasses import dataclass

from .ast_shared import (
    Var,
    ConstantInt,
    CFGFunction as _CFGFunction,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
)
from .tac_cfg import (
    BinOp,
    UnaryOp,
    AssignLHS,
    AssignRHS,
    Subscript,
    Assign,
    Jump,
    ConditionalJump,
    For,
    Return,
    BlockTerminator,
    BranchKind,
    List,
    Tuple,
    Mux,
    LoopBound,
    Atom,
    Operand,
)
from .tac_cfg import Block as _BaseBlock


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
class Block(_BaseBlock):
    phi_functions: list[Phi]

    def __str__(self) -> str:
        return (
            "\n".join([str(phi) for phi in self.phi_functions])
            + ("" if self.phi_functions == [] else "\n")
            + super().__str__()
        )


class Function(_CFGFunction[Block]):
    def compute_dominance_tree(self) -> dict[Block, list[Block]]:
        dominance_tree_dict: dict[
            Block, Block
        ] = networkx.algorithms.immediate_dominators(
            G=self.body, start=self.entry_block
        )

        result: dict[Block, list[Block]] = {block: [] for block in self.body.nodes}

        for k, v in dominance_tree_dict.items():
            if k == v:
                continue

            assert k not in result[v]
            result[v].append(k)

        return result
