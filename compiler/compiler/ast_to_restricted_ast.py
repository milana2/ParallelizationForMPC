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
    def visit_Name(self, node: ast.Name) -> str:
        return node.id


@dataclass
class _NameExpector(_StrictNodeVisitor):
    name: str

    def visit_Name(self, node: ast.Name):
        assert node.id == self.name


class _ConstantIntGetter(_StrictNodeVisitor):
    def visit_Constant(self, node: ast.Constant) -> int:
        assert type(node.value) == int
        return node.value


class _LoopBoundConverter(_StrictNodeVisitor):
    def visit_Constant(self, node: ast.Constant) -> int:
        assert type(node.value) == int
        return node.value

    def visit_Name(self, node: ast.Name) -> restricted_ast.Var:
        return restricted_ast.Var(name=node.id)


class _RangeBoundGetter(_StrictNodeVisitor):
    def visit_Call(self, node: ast.Call) -> int:
        _NameExpector("range").visit(node.func)
        assert node.keywords == []
        assert len(node.args) == 1 or (
            len(node.args) == 2 and _ConstantIntGetter().visit(node.args[0]) == 0
        )
        return _LoopBoundConverter().visit(node.args[-1])


def _convert_subscript(node: ast.Subscript) -> restricted_ast.Subscript:
    return restricted_ast.Subscript(
        array=_NameGetter().visit(node.value),
        index=_NameGetter().visit(node.slice),
    )


class _BinOpLHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> restricted_ast.Subscript:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> restricted_ast.Var:
        return restricted_ast.Var(name=node.id)


class _BinOpRHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> restricted_ast.Subscript:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> restricted_ast.Var:
        return restricted_ast.Var(name=node.id)

    def visit_Constant(self, node: ast.Constant) -> int:
        return node.value


class _AssignLHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> restricted_ast.Subscript:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> restricted_ast.Var:
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
        ast.Lt: restricted_ast.BinOpKind.LESS_THAN,
    }
    try:
        return TABLE[type(op)]
    except KeyError:
        assert False


class _AssignRHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> restricted_ast.Subscript:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> restricted_ast.Var:
        return restricted_ast.Var(name=node.id)

    def visit_BinOp(self, node: ast.BinOp) -> restricted_ast.BinOp:
        return restricted_ast.BinOp(
            left=_BinOpLHSConverter().visit(node.left),
            operator=_convert_binary_operator(node.op),
            right=_BinOpRHSConverter().visit(node.right),
        )

    def visit_Constant(self, node: ast.Constant) -> restricted_ast.ConstantInt:
        return restricted_ast.ConstantInt(value=node.value)


def _convert_statements(statements: list[ast.stmt]) -> list[restricted_ast.Statement]:
    result: list[restricted_ast.Statement] = [
        _StatementConverter().visit(statement) for statement in statements
    ]
    # Ensure there isn't a return in the middle of a list of statements
    assert (
        len(
            [
                statement
                for statement in result[:-1]
                if isinstance(statement, restricted_ast.Return)
            ]
        )
        == 0
    )
    return result


class _StatementConverter(_StrictNodeVisitor):
    def visit_For(self, node: ast.For) -> restricted_ast.For:
        assert node.orelse == []
        return restricted_ast.For(
            counter=_NameGetter().visit(node.target),
            bound=_RangeBoundGetter().visit(node.iter),
            body=_convert_statements(node.body),
        )

    def visit_If(self, node: ast.If) -> restricted_ast.If:
        return restricted_ast.If(
            condition=_NameGetter().visit(node.test),
            then_body=_convert_statements(node.body),
            else_body=_convert_statements(node.orelse),
        )

    def visit_Assign(self, node: ast.Assign) -> restricted_ast.Assign:
        assert len(node.targets) == 1
        return restricted_ast.Assign(
            lhs=_AssignLHSConverter().visit(node.targets[0]),
            rhs=_AssignRHSConverter().visit(node.value),
        )

    def visit_Return(self, node: ast.Return) -> restricted_ast.Return:
        assert node.value is not None
        return restricted_ast.Return(value=_NameGetter().visit(node.value))


class _FunctionConverter(_StrictNodeVisitor):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> restricted_ast.Function:
        # TODO: Check parameter and return types
        assert node.decorator_list == []
        return restricted_ast.Function(
            # TODO: Exclude other kinds of arguments
            parameters=[restricted_ast.Var(name=arg.arg) for arg in node.args.args],
            body=_convert_statements(node.body),
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
