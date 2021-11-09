"""
Tools for converting from a restricted subset of Python's AST to
a three-address code control flow graph
"""


import networkx

from . import restricted_ast
from . import tac_cfg
from .util import assert_never


class _CFGBuilder:
    _cfg: networkx.DiGraph
    _entry_block: tac_cfg.Block
    _current_block: tac_cfg.Block
    _tmp_name_counter: int = 0

    def __init__(self):
        self._cfg = networkx.DiGraph()
        self._entry_block = self.make_empty_block()
        self._current_block = self._entry_block

    def generate_variable(self) -> tac_cfg.Var:
        self._tmp_name_counter += 1
        return tac_cfg.Var(name=f"!{self._tmp_name_counter}")

    def make_empty_block(self) -> tac_cfg.Block:
        block = tac_cfg.Block(assignments=[], terminator=None, merge_condition=None)
        self._cfg.add_node(block)
        return block

    def get_current_block(self) -> tac_cfg.Block:
        return self._current_block

    def set_current_block(self, block: tac_cfg.Block):
        self._current_block = block
        assert self._current_block.terminator is None

    def current_block_done(self) -> bool:
        return self._current_block.terminator is not None

    def add_assignment(self, assignment: tac_cfg.Assign):
        assert self._current_block.terminator is None
        self._current_block.assignments.append(assignment)

    def add_jump(self, target_block: tac_cfg.Block):
        assert self._current_block.terminator is None
        self._current_block.terminator = tac_cfg.Jump()
        self._cfg.add_edge(
            u_of_edge=self._current_block,
            v_of_edge=target_block,
            label=tac_cfg.BranchKind.UNCONDITIONAL,
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
            label=tac_cfg.BranchKind.FALSE,
        )
        self._cfg.add_edge(
            u_of_edge=self._current_block,
            v_of_edge=true_block,
            label=tac_cfg.BranchKind.TRUE,
        )

    def build_function(
        self, parameters: list[tac_cfg.Var], return_var: tac_cfg.Var
    ) -> tac_cfg.Function:
        assert self._current_block.terminator is None
        self._current_block.terminator = tac_cfg.Return(value=return_var)
        return tac_cfg.Function(
            parameters=parameters,
            body=self._cfg,
            entry_block=self._entry_block,
            exit_block=self._current_block,
        )


def _build_expression(
    expression: restricted_ast.Expression, builder: _CFGBuilder
) -> tac_cfg.Var:
    if isinstance(expression, restricted_ast.Var):
        return expression
    elif isinstance(expression, restricted_ast.ConstantInt):
        result_var = builder.generate_variable()
        builder.add_assignment(tac_cfg.Assign(lhs=result_var, rhs=expression))
        return result_var
    elif isinstance(expression, restricted_ast.Index):
        index_var = _build_expression(expression.index, builder)
        result_var = builder.generate_variable()
        builder.add_assignment(
            tac_cfg.Assign(
                lhs=result_var,
                rhs=tac_cfg.Index(array=expression.array, index=index_var),
            )
        )
        return result_var
    elif isinstance(expression, restricted_ast.List):
        item_vars = [_build_expression(item, builder) for item in expression.items]
        result_var = builder.generate_variable()
        builder.add_assignment(
            tac_cfg.Assign(
                lhs=result_var,
                rhs=tac_cfg.List(items=item_vars),
            )
        )
        return result_var
    elif isinstance(expression, restricted_ast.BinOp):
        left_var = _build_expression(expression.left, builder)
        right_var = _build_expression(expression.right, builder)
        result_var = builder.generate_variable()
        builder.add_assignment(
            tac_cfg.Assign(
                lhs=result_var,
                rhs=tac_cfg.BinOp(
                    left=left_var,
                    operator=expression.operator,
                    right=right_var,
                ),
            )
        )
        return result_var
    elif isinstance(expression, restricted_ast.UnaryOp):
        operand_var = _build_expression(expression.operand, builder)
        result_var = builder.generate_variable()
        builder.add_assignment(
            tac_cfg.Assign(
                lhs=result_var,
                rhs=tac_cfg.UnaryOp(
                    operator=expression.operator,
                    operand=operand_var,
                ),
            )
        )
        return result_var
    else:
        assert_never(expression)


def _build_assignment(assignment: restricted_ast.Assign, builder: _CFGBuilder):
    if isinstance(assignment.lhs, restricted_ast.Index):
        lhs = tac_cfg.Index(
            array=assignment.lhs.array,
            index=_build_expression(assignment.lhs.index, builder),
        )
    else:
        lhs = assignment.lhs

    builder.add_assignment(
        tac_cfg.Assign(
            lhs=lhs,
            rhs=_build_expression(assignment.rhs, builder),
        )
    )


def _build_if(if_statement: restricted_ast.If, builder: _CFGBuilder):
    condition_block = builder.get_current_block()
    then_block = builder.make_empty_block()
    else_block = builder.make_empty_block()
    after_block = builder.make_empty_block()

    builder.add_conditional_jump(
        condition=_build_expression(if_statement.condition, builder),
        false_block=else_block,
        true_block=then_block,
    )

    builder.set_current_block(then_block)
    _build_statements(if_statement.then_body, builder)
    if not builder.current_block_done():
        builder.add_jump(after_block)

    builder.set_current_block(else_block)
    _build_statements(if_statement.else_body, builder)
    if not builder.current_block_done():
        builder.add_jump(after_block)

    builder.set_current_block(after_block)
    assert isinstance(condition_block.terminator, tac_cfg.ConditionalJump)
    after_block.merge_condition = condition_block.terminator


def _build_for(for_loop: restricted_ast.For, builder: _CFGBuilder):
    # counter = bound_low
    builder.add_assignment(tac_cfg.Assign(lhs=for_loop.counter, rhs=for_loop.bound_low))

    # bound_high_var = bound_high
    bound_var = builder.generate_variable()
    builder.add_assignment(tac_cfg.Assign(lhs=bound_var, rhs=for_loop.bound_high))

    # Jump to a new block so the end of the loop can jump back here
    condition_block = builder.make_empty_block()
    builder.add_jump(condition_block)
    builder.set_current_block(condition_block)

    # condition_var = counter < bound_high
    condition_var = builder.generate_variable()
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

    # Increment loop counter

    # one = 1
    one_var = builder.generate_variable()
    builder.add_assignment(
        tac_cfg.Assign(
            lhs=one_var,
            rhs=tac_cfg.ConstantInt(1),
        )
    )

    # counter = counter + one
    builder.add_assignment(
        tac_cfg.Assign(
            lhs=for_loop.counter,
            rhs=tac_cfg.BinOp(
                left=for_loop.counter,
                operator=tac_cfg.BinOpKind.ADD,
                right=one_var,
            ),
        )
    )

    # Jump back to condition
    if not builder.current_block_done():
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
        else:
            assert_never(statement)


def restricted_ast_to_tac_cfg(node: restricted_ast.Function) -> tac_cfg.Function:
    builder = _CFGBuilder()
    _build_statements(node.body, builder)
    return_var = _build_expression(node.return_value, builder)
    return builder.build_function(node.parameters, return_var)
