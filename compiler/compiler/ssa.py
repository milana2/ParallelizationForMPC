"""Data types representing code in static single assignment form"""

from dataclasses import dataclass

import networkx  # type: ignore

from .ast_shared import (
    Var,
    Constant,
    CFGFunction as _CFGFunction,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
)
from .tac_cfg import (
    BinOp,
    UnaryOp,
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
    Update,
)
from .tac_cfg import Block as _BaseBlock


@dataclass(eq=False)
class Phi:
    lhs: Var
    rhs_false: Var
    rhs_true: Var

    def rhs_vars(self) -> list[Var]:
        return [self.rhs_false, self.rhs_true]

    def __hash__(self):
        return id(self)

    def __str__(self) -> str:
        return f"{self.lhs} = Φ({self.rhs_false}, {self.rhs_true})"


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
