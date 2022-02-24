"""Data types representing code in static single assignment form"""

from dataclasses import dataclass
from typing import Union

import networkx  # type: ignore

from .ast_shared import (
    Var,
    Constant,
    CFGFunction as _CFGFunction,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
    VectorizedAccess,
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
    assign_rhs_accessed_vars,
)
from .tac_cfg import Block as _BaseBlock
from .util import assert_never


@dataclass(eq=False)
class Phi:
    lhs: Union[Var, VectorizedAccess]
    rhs_false: Union[Var, VectorizedAccess]
    rhs_true: Union[Var, VectorizedAccess]

    def rhs_vars(self) -> list[Var]:
        if isinstance(self.rhs_false, Var):
            rhs_false_var = self.rhs_false
        elif isinstance(self.rhs_false, VectorizedAccess):
            rhs_false_var = self.rhs_false.array
        else:
            assert_never(self.rhs_false)

        if isinstance(self.rhs_true, Var):
            rhs_true_var = self.rhs_true
        elif isinstance(self.rhs_true, VectorizedAccess):
            rhs_true_var = self.rhs_true.array
        else:
            assert_never(self.rhs_true)

        return [rhs_false_var, rhs_true_var]

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
