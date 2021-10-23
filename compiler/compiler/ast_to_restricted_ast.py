"""
Tools for checking if a Python AST fits a restricted subset,
and for converting to a data type that reflects that restricted subset.
"""

import ast
from dataclasses import dataclass

import restricted_ast


class _StrictNodeVisitor(ast.NodeVisitor):
    def generic_visit(self, node: ast.AST):
        assert False


class _NameGetter(_StrictNodeVisitor):
    def visit_Name(self, node: ast.Name) -> restricted_ast.Var:
        return restricted_ast.Var(node.id)


@dataclass
class _NameExpector(_StrictNodeVisitor):
    name: str

    def visit_Name(self, node: ast.Name):
        assert node.id == self.name


class _LoopBoundConverter(_StrictNodeVisitor):
    def visit_Constant(self, node: ast.Constant) -> restricted_ast.LoopBound:
        assert type(node.value) == int
        return node.value

    def visit_Name(self, node: ast.Name) -> restricted_ast.LoopBound:
        return restricted_ast.Var(name=node.id)


class _RangeBoundsGetter(_StrictNodeVisitor):
    def visit_Call(
        self, node: ast.Call
    ) -> tuple[restricted_ast.LoopBound, restricted_ast.LoopBound]:
        _NameExpector("range").visit(node.func)
        assert node.keywords == []
        bounds = [_LoopBoundConverter().visit(arg) for arg in node.args]
        if len(bounds) == 1:
            return (restricted_ast.ConstantInt(0), bounds[0])
        elif len(bounds) == 2:
            return (bounds[0], bounds[1])
        else:
            assert False


def _convert_subscript(node: ast.Subscript) -> restricted_ast.Index:
    return restricted_ast.Index(
        array=_NameGetter().visit(node.value),
        index=_ExpressionConverter().visit(node.slice),
    )


class _AssignLHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> restricted_ast.AssignLHS:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> restricted_ast.AssignLHS:
        return restricted_ast.Var(name=node.id)


def _convert_binary_operator(op: ast.operator) -> restricted_ast.BinOpKind:
    TABLE: dict[type[ast.operator], restricted_ast.BinOpKind] = {
        ast.Add: restricted_ast.BinOpKind.ADD,
        ast.Sub: restricted_ast.BinOpKind.SUB,
        ast.Mult: restricted_ast.BinOpKind.MUL,
        ast.FloorDiv: restricted_ast.BinOpKind.DIV,
        ast.Mod: restricted_ast.BinOpKind.MOD,
        ast.LShift: restricted_ast.BinOpKind.SHL,
        ast.RShift: restricted_ast.BinOpKind.SHR,
    }
    try:
        return TABLE[type(op)]
    except KeyError:
        assert False


class _ExpressionConverter(_StrictNodeVisitor):
    def visit_Name(self, node: ast.Name) -> restricted_ast.Expression:
        return restricted_ast.Var(name=node.id)

    def visit_Constant(self, node: ast.Constant) -> restricted_ast.Expression:
        return restricted_ast.ConstantInt(value=node.value)

    def visit_Subscript(self, node: ast.Subscript) -> restricted_ast.Expression:
        return _convert_subscript(node)

    def visit_BinOp(self, node: ast.BinOp) -> restricted_ast.Expression:
        return restricted_ast.BinOp(
            left=_ExpressionConverter().visit(node.left),
            operator=_convert_binary_operator(node.op),
            right=_ExpressionConverter().visit(node.right),
        )

    def visit_Compare(self, node: ast.Compare) -> restricted_ast.Expression:
        assert len(node.ops) == 1
        assert type(node.ops[0]) == ast.Lt
        assert len(node.comparators) == 1
        return restricted_ast.BinOp(
            left=_ExpressionConverter().visit(node.left),
            operator=restricted_ast.BinOpKind.LESS_THAN,
            right=_ExpressionConverter().visit(node.comparators[0]),
        )

    def visit_UnaryOp(self, node: ast.UnaryOp) -> restricted_ast.Expression:
        assert type(node.op) == ast.USub
        return restricted_ast.UnaryOp(
            operator=restricted_ast.UnaryOpKind.NEGATE,
            operand=_ExpressionConverter().visit(node.operand),
        )


def _convert_statements(statements: list[ast.stmt]) -> list[restricted_ast.Statement]:
    return [_StatementConverter().visit(statement) for statement in statements]


class _StatementConverter(_StrictNodeVisitor):
    def visit_For(self, node: ast.For) -> restricted_ast.For:
        assert node.orelse == []
        (bound_low, bound_high) = _RangeBoundsGetter().visit(node.iter)
        return restricted_ast.For(
            counter=_NameGetter().visit(node.target),
            bound_low=bound_low,
            bound_high=bound_high,
            body=_convert_statements(node.body),
        )

    def visit_If(self, node: ast.If) -> restricted_ast.If:
        return restricted_ast.If(
            condition=_ExpressionConverter().visit(node.test),
            then_body=_convert_statements(node.body),
            else_body=_convert_statements(node.orelse),
        )

    def visit_Assign(self, node: ast.Assign) -> restricted_ast.Assign:
        assert len(node.targets) == 1
        return restricted_ast.Assign(
            lhs=_AssignLHSConverter().visit(node.targets[0]),
            rhs=_ExpressionConverter().visit(node.value),
        )

    def visit_AnnAssign(self, node: ast.AnnAssign) -> restricted_ast.Assign:
        assert node.value is not None
        return restricted_ast.Assign(
            lhs=_AssignLHSConverter().visit(node.target),
            rhs=_ExpressionConverter().visit(node.value),
        )


class _ReturnVarGetter(_StrictNodeVisitor):
    def visit_Return(self, node: ast.Return) -> restricted_ast.Var:
        assert node.value is not None
        return _NameGetter().visit(node.value)


class _FunctionConverter(_StrictNodeVisitor):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> restricted_ast.Function:
        # TODO: Check parameter and return types
        assert node.decorator_list == []
        assert len(node.body) != 0
        return restricted_ast.Function(
            # TODO: Exclude other kinds of arguments
            parameters=[restricted_ast.Var(name=arg.arg) for arg in node.args.args],
            body=_convert_statements(node.body[:-1]),
            return_var=_ReturnVarGetter().visit(node.body[-1]),
        )


class _ModuleConverter(_StrictNodeVisitor):
    def visit_Module(self, node: ast.Module) -> restricted_ast.Function:
        # TODO: Support larger modules
        return _FunctionConverter().visit(
            [
                statement
                for statement in node.body
                if type(statement) == ast.FunctionDef
            ][0]
        )


def ast_to_restricted_ast(node: ast.AST) -> restricted_ast.Function:
    return _ModuleConverter().visit(node)
