"""
Tools for converting a subset of Python ASTs to three-address code.
"""

import ast
from dataclasses import dataclass

import tac


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

    def visit_Name(self, node: ast.Name) -> tac.Var:
        return tac.Var(name=node.id)


class _RangeBoundGetter(_StrictNodeVisitor):
    def visit_Call(self, node: ast.Call) -> int:
        _NameExpector("range").visit(node.func)
        assert node.keywords == []
        assert len(node.args) == 1 or (
            len(node.args) == 2 and _ConstantIntGetter().visit(node.args[0]) == 0
        )
        return _LoopBoundConverter().visit(node.args[-1])


def _convert_subscript(node: ast.Subscript) -> tac.Subscript:
    return tac.Subscript(
        array=_NameGetter().visit(node.value),
        index=_NameGetter().visit(node.slice),
    )


class _BinOpLHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> tac.Subscript:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> tac.Var:
        return tac.Var(name=node.id)


class _BinOpRHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> tac.Subscript:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> tac.Var:
        return tac.Var(name=node.id)

    def visit_Constant(self, node: ast.Constant) -> int:
        return node.value


class _AssignLHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> tac.Subscript:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> tac.Var:
        return tac.Var(name=node.id)


def _convert_binary_operator(op: ast.operator) -> tac.BinOpKind:
    TABLE: dict[type[ast.operator], tac.BinOpKind] = {
        ast.Add: tac.BinOpKind.ADD,
        ast.Sub: tac.BinOpKind.SUB,
        ast.Mult: tac.BinOpKind.MUL,
        ast.FloorDiv: tac.BinOpKind.DIV,
        ast.Mod: tac.BinOpKind.MOD,
        ast.LShift: tac.BinOpKind.SHL,
        ast.RShift: tac.BinOpKind.SHR,
    }
    try:
        return TABLE[type(op)]
    except KeyError:
        assert False


class _AssignRHSConverter(_StrictNodeVisitor):
    def visit_Subscript(self, node: ast.Subscript) -> tac.Subscript:
        return _convert_subscript(node)

    def visit_Name(self, node: ast.Name) -> tac.Var:
        return tac.Var(name=node.id)

    def visit_BinOp(self, node: ast.BinOp) -> tac.BinOp:
        return tac.BinOp(
            left=_BinOpLHSConverter().visit(node.left),
            operator=_convert_binary_operator(node.op),
            right=_BinOpRHSConverter().visit(node.right),
        )

    def visit_Constant(self, node: ast.Constant) -> int:
        return node.value


def _convert_statements(statements: list[ast.stmt]):
    return [_StatementConverter().visit(statement) for statement in statements]


class _StatementConverter(_StrictNodeVisitor):
    def visit_For(self, node: ast.For) -> tac.For:
        assert node.orelse == []
        return tac.For(
            counter=_NameGetter().visit(node.target),
            bound=_RangeBoundGetter().visit(node.iter),
            body=_convert_statements(node.body),
        )

    def visit_If(self, node: ast.If) -> tac.If:
        return tac.If(
            condition=_NameGetter().visit(node.test),
            then_body=_convert_statements(node.body),
            else_body=_convert_statements(node.orelse),
        )

    def visit_Assign(self, node: ast.Assign) -> tac.Assign:
        assert len(node.targets) == 1
        return tac.Assign(
            lhs=_AssignLHSConverter().visit(node.targets[0]),
            rhs=_AssignRHSConverter().visit(node.value),
        )

    def visit_Return(self, node: ast.Return) -> tac.Return:
        assert node.value is not None
        return tac.Return(value=_NameGetter().visit(node.value))


class _FunctionConverter(_StrictNodeVisitor):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> tac.Function:
        # TODO: Check parameter and return types
        assert node.decorator_list == []
        return tac.Function(
            # TODO: Exclude other kinds of arguments
            parameters=[tac.Var(name=arg.arg) for arg in node.args.args],
            body=_convert_statements(node.body),
        )


class _ModuleConverter(_StrictNodeVisitor):
    def visit_Module(self, node: ast.Module) -> tac.Function:
        # TODO: Support larger modules
        return _FunctionConverter().visit(
            [
                statement
                for statement in node.body
                if type(statement) == ast.FunctionDef
            ][0]
        )


def ast_to_tac(node: ast.AST) -> tac.Function:
    return _ModuleConverter().visit(node)
