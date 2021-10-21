"""
Tools for converting from a restricted subset of Python's AST to
a three-address code control flow graph
"""


import networkx

import restricted_ast
import tac_cfg
from util import assert_never

_TMP_NAME_COUNTER = 0


def _generate_variable() -> tac_cfg.Var:
    global _TMP_NAME_COUNTER
    _TMP_NAME_COUNTER += 1
    return tac_cfg.Var(name=f"!{_TMP_NAME_COUNTER}")


class _CFGBuilder:
    _cfg: networkx.DiGraph
    _entry_block: tac_cfg.Block
    _exit_block: tac_cfg.Block
    _current_block: tac_cfg.Block
    _return_variable: tac_cfg.Var

    def __init__(self):
        self._cfg = networkx.DiGraph()
        self._entry_block = self.make_empty_block()
        self._return_variable = _generate_variable()
        self._exit_block = tac_cfg.Block(
            assignments=[],
            terminator=tac_cfg.Return(value=self._return_variable),
        )
        self._current_block = self._entry_block

    def make_empty_block(self) -> tac_cfg.Block:
        return tac_cfg.Block(assignments=[], terminator=None)

    def set_current_block(self, block: tac_cfg.Block):
        self._current_block = block
        assert self._current_block.terminator is None

    def add_assignment(self, assignment: tac_cfg.Assign):
        assert self._current_block.terminator is None
        self._current_block.assignments.append(assignment)

    def add_return(self, var: tac_cfg.Var):
        assert self._current_block.terminator is None
        self.add_assignment(tac_cfg.Assign(self._return_variable, var))
        self._current_block.terminator = tac_cfg.Jump()
        self._cfg.add_edge(self._current_block, self._exit_block)

    def add_jump(self, target_block: tac_cfg.Block):
        assert self._current_block.terminator is None
        self._current_block.terminator = tac_cfg.Jump()
        self._cfg.add_edge(
            u_of_edge=self._current_block,
            v_of_edge=target_block,
            branch_kind=tac_cfg.BranchKind.UNCONDITIONAL,
        )

    def add_conditional_jump(
        self,
        condition: tac_cfg.Var,
        false_block: tac_cfg.Block,
        true_block: tac_cfg.Block,
    ):
        assert self._current_block.terminator is None
        self._current_block.terminator = tac_cfg.ConditionalJump(condition)
        self._cfg.add_edge(
            u_of_edge=self._current_block,
            v_of_edge=false_block,
            branch_kind=tac_cfg.BranchKind.FALSE,
        )
        self._cfg.add_edge(
            u_of_edge=self._current_block,
            v_of_edge=true_block,
            branch_kind=tac_cfg.BranchKind.TRUE,
        )

    def build_function(self, parameters: list[tac_cfg.Var]) -> tac_cfg.Function:
        assert self._current_block.terminator is not None
        return tac_cfg.Function(
            parameters=parameters,
            body=self._cfg,
            entry_block=self._entry_block,
            exit_block=self._exit_block,
        )


def _build_assignment(assignment: restricted_ast.Assign, builder: _CFGBuilder):
    if (
        isinstance(assignment.rhs, restricted_ast.Subscript)
        or isinstance(assignment.rhs, restricted_ast.Var)
        or isinstance(assignment.rhs, restricted_ast.ConstantInt)
    ):
        builder.add_assignment(tac_cfg.Assign(lhs=assignment.lhs, rhs=assignment.rhs))
    elif isinstance(assignment.rhs, restricted_ast.BinOp):
        bin_op = assignment.rhs

        if isinstance(bin_op.left, restricted_ast.Subscript):
            tmp_var = _generate_variable()
            builder.add_assignment(tac_cfg.Assign(lhs=tmp_var, rhs=bin_op.left))
            left = tmp_var
        elif isinstance(bin_op.left, restricted_ast.Var):
            left = bin_op.left
        else:
            assert_never(bin_op.left)

        if isinstance(bin_op.right, restricted_ast.Subscript) or isinstance(
            bin_op.right, restricted_ast.ConstantInt
        ):
            tmp_var = _generate_variable()
            builder.add_assignment(tac_cfg.Assign(lhs=tmp_var, rhs=bin_op.right))
            right = tmp_var
        elif isinstance(bin_op.right, restricted_ast.Var):
            right = bin_op.right
        else:
            assert_never(bin_op.right)

        builder.add_assignment(tac_cfg.Assign(lhs=left, rhs=right))
    else:
        assert_never(assignment.rhs)


def _build_if(if_statement: restricted_ast.If, builder: _CFGBuilder):
    then_block = builder.make_empty_block()
    else_block = builder.make_empty_block()
    after_block = builder.make_empty_block()

    builder.add_conditional_jump(
        condition=if_statement.condition,
        false_block=else_block,
        true_block=then_block,
    )

    builder.set_current_block(then_block)
    _build_statements(if_statement.then_body, builder)
    if then_block.terminator is None:
        builder.add_jump(after_block)

    builder.set_current_block(else_block)
    _build_statements(if_statement.else_body, builder)
    if else_block.terminator is None:
        builder.add_jump(after_block)

    builder.set_current_block(after_block)


def _build_for(for_loop: restricted_ast.For, builder: _CFGBuilder):
    # counter = 0
    builder.add_assignment(
        tac_cfg.Assign(lhs=for_loop.counter, rhs=tac_cfg.ConstantInt(value=0))
    )

    # bound_var = bound
    bound_var = _generate_variable()
    builder.add_assignment(tac_cfg.Assign(lhs=bound_var, rhs=for_loop.bound))

    # Jump to a new block so the end of the loop can jump back here
    condition_block = builder.make_empty_block()
    builder.add_jump(condition_block)
    builder.set_current_block(condition_block)

    # condition_var = counter < bound
    condition_var = _generate_variable()
    builder.add_assignment(
        tac_cfg.Assign(
            lhs=condition_var,
            rhs=tac_cfg.BinOp(
                left=for_loop.counter,
                operator=tac_cfg.BinOpKind.LESS_THAN,
                right=bound_var,
            ),
        )
    )

    # Block for loop body
    body_block = builder.make_empty_block()

    # Block for code after the loop
    after_block = builder.make_empty_block()

    # Condition for whether to terminate or continue the loop
    builder.add_conditional_jump(
        condition=condition_var,
        false_block=after_block,
        true_block=body_block,
    )

    # Add the loop body
    builder.set_current_block(body_block)
    _build_statements(for_loop.body, builder)
    if body_block.terminator is None:
        builder.add_jump(condition_block)

    # Move to end of loop
    builder.set_current_block(after_block)


def _build_statements(statements: list[restricted_ast.Statement], builder: _CFGBuilder):
    for statement in statements:
        if isinstance(statement, restricted_ast.For):
            _build_for(statement, builder)
        elif isinstance(statement, restricted_ast.If):
            _build_if(statement, builder)
        elif isinstance(statement, restricted_ast.Assign):
            _build_assignment(statement, builder)
        elif isinstance(statement, restricted_ast.Return):
            builder.add_return(statement.value)
        else:
            assert_never(statement)


def restricted_ast_to_tac_cfg(node: restricted_ast.Function) -> tac_cfg.Function:
    builder = _CFGBuilder()
    _build_statements(node.body, builder)
    return builder.build_function(node.parameters)
