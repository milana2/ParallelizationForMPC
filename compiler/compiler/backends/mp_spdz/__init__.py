from textwrap import indent
from typing import Any, Optional, Union

from ...util import assert_never
from ...loop_linear_code import (
    Parameter,
    Function,
    Statement,
    Phi,
    Assign,
    For,
    Return,
    Update,
    VectorizedAccess,
    VectorizedUpdate,
    Var,
    BinOp,
    BinOpKind,
    SubscriptIndexBinOp,
    List,
    Tuple,
    Mux,
    UnaryOp,
    UnaryOpKind,
    Subscript,
    SubscriptIndex,
    SubscriptIndexBinOp,
    SubscriptIndexUnaryOp,
    Atom,
    LiftExpr,
    DropDim,
    LoopBound,
)
from ...type_analysis import TypeEnv, Constant


UpdatelessAssignRHS = Union[
    Atom, Subscript, BinOp, UnaryOp, List, Tuple, Mux, LiftExpr, DropDim
]


VALID_PROTOCOLS = [
    "mascot",
    "lowgear",
    "highgear",
    "spdz2k",
    "tiny",
    "tinier",
    "bmr",
    "cowgear",
    "chaigear",
    "semi",
    "hemi",
    "temi",
    "soho",
    "semi2k",
    "semibin",
    "yao-gc",
    "yao-bmr",
    "shamir",
    "rep3",
    "ps",
    "sy",
    "brain",
    "ccd",
    "atlas",
    "rep4",
    "dealer",
]


def render_var(var: Var, var_mappings: dict[Var, str]) -> str:
    try:
        return var_mappings[var]
    except KeyError:
        return str(var).replace("!", "_")


def render_array_slice(v: VectorizedAccess, var_mappings: dict[Var, str]) -> str:
    assert len(v.dim_sizes) == 1
    if v.vectorized_dims[0]:
        return ":"
    else:
        return render_var(v.idx_vars[0], var_mappings)


def render_multi_array_slice(v: VectorizedAccess, var_mappings: dict[Var, str]) -> str:
    return ", ".join(
        [
            "None" if vectorized else render_var(var, var_mappings)
            for vectorized, var in zip(v.vectorized_dims, v.idx_vars)
        ]
    )


def render_vectorized_access(v: VectorizedAccess, var_mappings: dict[Var, str]) -> str:
    array = render_var(v.array, var_mappings)
    if len(v.dim_sizes) == 1:
        slice = render_array_slice(v, var_mappings)
        return f"{array}[{slice}]"
    else:
        slice = render_multi_array_slice(v, var_mappings)
        return f"{array}.get_vector_by_indices({slice})"


def render_vectorized_assign(lhs: VectorizedAccess, rhs: UpdatelessAssignRHS) -> str:
    array = render_atom(lhs.array, dict())
    value = render_assign_rhs(rhs, dict())
    if len(lhs.dim_sizes) == 1:
        slice = render_array_slice(lhs, dict())
        return f"{array}[{slice}] = {value}"
    else:
        slice = render_multi_array_slice(lhs, dict())
        return f"{array}.assign_vector_by_indices(({value}).get_vector(), {slice})"


def render_atom(atom: Atom, var_mappings: dict[Var, str]) -> str:
    if isinstance(atom, Var):
        return render_var(atom, var_mappings)
    elif isinstance(atom, Constant):
        return str(atom)
    elif isinstance(atom, VectorizedAccess):
        return render_vectorized_access(atom, var_mappings)
    else:
        assert_never(atom)


def render_bin_op_kind(op: BinOpKind) -> str:
    if op == BinOpKind.AND:
        return "&"
    elif op == BinOpKind.OR:
        return "|"
    else:
        return str(op)


def render_unary_op_kind(op: UnaryOpKind) -> str:
    if op is UnaryOpKind.NEGATE:
        return "-"
    elif op is UnaryOpKind.NOT:
        return "~"
    else:
        assert_never(op)


def render_subscript_index(index: SubscriptIndex, var_mappings: dict[Var, str]) -> str:
    if isinstance(index, (Var, Constant)):
        return render_atom(index, var_mappings)
    elif isinstance(index, SubscriptIndexBinOp):
        left = render_subscript_index(index.left, var_mappings)
        operator = render_bin_op_kind(index.operator)
        right = render_subscript_index(index.right, var_mappings)
        return f"({left} {operator} {right})"
    elif isinstance(index, SubscriptIndexUnaryOp):
        operator = render_unary_op_kind(index.operator)
        operand = render_subscript_index(index.operand, var_mappings)
        return f"({operator}{operand})"
    else:
        assert_never(index)


def render_lift_expr(lift: LiftExpr) -> str:
    assert not isinstance(lift.expr, (Update, VectorizedUpdate))
    expr = render_assign_rhs(
        lift.expr,
        {var: f"indices[{index}]" for index, (var, _) in enumerate(lift.dims)},
    )
    dim_sizes = ", ".join(render_atom(size, dict()) for (_, size) in lift.dims)
    return f"lift(lambda indices: sint({expr}), [{dim_sizes}])"


def render_assign_rhs(
    arhs: UpdatelessAssignRHS,
    var_mappings: dict[Var, str],
) -> str:
    if isinstance(arhs, BinOp):
        left = render_assign_rhs(arhs.left, var_mappings)
        right = render_assign_rhs(arhs.right, var_mappings)
        return f"({left} {arhs.operator} {right})"
    elif isinstance(arhs, (Var, Constant, VectorizedAccess)):
        return render_atom(arhs, var_mappings)
    elif isinstance(arhs, List):
        items = [render_atom(item, var_mappings) for item in arhs.items]
        comma_separated_items = ", ".join(items)
        return f"[{comma_separated_items}]"
    elif isinstance(arhs, Tuple):
        items = "".join(render_atom(item, var_mappings) + "," for item in arhs.items)
        return f"({items})"
    elif isinstance(arhs, Mux):
        condition = render_assign_rhs(arhs.condition, var_mappings)
        true_value = render_assign_rhs(arhs.true_value, var_mappings)
        false_value = render_assign_rhs(arhs.false_value, var_mappings)
        return f"{condition}.if_else({true_value}, {false_value})"
    elif isinstance(arhs, UnaryOp):
        operator = render_unary_op_kind(arhs.operator)
        operand = render_assign_rhs(arhs.operand, var_mappings)
        return f"({operator}{operand})"
    elif isinstance(arhs, Subscript):
        array = render_assign_rhs(arhs.array, var_mappings)
        index = render_subscript_index(arhs.index, var_mappings)
        return f"({array}[{index}])"
    elif isinstance(arhs, LiftExpr):
        return render_lift_expr(arhs)
    elif isinstance(arhs, DropDim):
        if isinstance(arhs.array, VectorizedAccess):
            assert all(arhs.array.vectorized_dims)
            array_var = arhs.array.array
        else:
            array_var = arhs.array
        array = render_var(array_var, var_mappings)
        return f"drop_dim({array})"
    else:
        return assert_never(arhs)


def render_statement(stmt: Statement, containing_loop: Optional[For]) -> str:
    if isinstance(stmt, Phi):
        assert containing_loop
        assert isinstance(containing_loop.bound_low, Constant)
        assert containing_loop.bound_low.value == 0
        loop_counter = render_var(containing_loop.counter, dict())
        phi_assign_false = render_statement(
            Assign(lhs=stmt.lhs, rhs=stmt.rhs_false), None
        )
        phi_assign_true = render_statement(
            Assign(lhs=stmt.lhs, rhs=stmt.rhs_true), None
        )
        return (
            f"# Set ϕ value\n"
            + f"if {loop_counter} == 0:\n"
            + f"    {phi_assign_false}\n"
            + f"else:\n"
            + f"    {phi_assign_true}"
        )
    elif isinstance(stmt, Assign):
        lhs = render_atom(stmt.lhs, dict())
        if isinstance(stmt.rhs, Update):
            array = render_var(stmt.rhs.array, dict())
            index = render_subscript_index(stmt.rhs.index, dict())
            value = render_atom(stmt.rhs.value, dict())
            return f"{array}[{index}] = {value}; {lhs} = {array}"
        elif isinstance(stmt.rhs, VectorizedUpdate):
            rhs_array_access = VectorizedAccess(
                array=stmt.rhs.array,
                dim_sizes=stmt.rhs.dim_sizes,
                vectorized_dims=stmt.rhs.vectorized_dims,
                idx_vars=stmt.rhs.idx_vars,
            )
            assign1 = render_vectorized_assign(
                lhs=rhs_array_access,
                rhs=stmt.rhs.value,
            )
            assign2 = render_statement(
                Assign(lhs=stmt.lhs, rhs=rhs_array_access), containing_loop
            )
            return f"{assign1}; {assign2}"
        elif isinstance(stmt.lhs, VectorizedAccess):
            return render_vectorized_assign(stmt.lhs, stmt.rhs)
        else:
            rhs = render_assign_rhs(stmt.rhs, dict())
            return f"{lhs} = {rhs}"
    elif isinstance(stmt, For):
        counter = render_var(stmt.counter, dict())
        bound_low = render_atom(stmt.bound_low, dict())
        bound_high = render_atom(stmt.bound_high, dict())
        body = indent(render_statements(stmt.body, stmt), "    ")
        return f"for {counter} in range({bound_low}, {bound_high}):\n{body}"
    elif isinstance(stmt, Return):
        value = render_var(stmt.value, dict())
        return f"return {value}"
    else:
        assert_never(stmt)


def render_statements(stmts: list[Statement], containing_loop: Optional[For]) -> str:
    return "\n".join(render_statement(stmt, containing_loop) for stmt in stmts)


def render_shared_array_decl(var: Var, dim_sizes: list[LoopBound]) -> str:
    var_rendered = render_var(var, dict())
    dim_sizes_rendered = ", ".join(
        [render_atom(dim_size, dict()) for dim_size in dim_sizes]
    )
    return f"{var_rendered} = sint.Tensor([{dim_sizes_rendered}])"


def render_shared_array_decls(type_env: TypeEnv) -> str:
    return "\n".join(
        [
            render_shared_array_decl(var, var_type.dim_sizes)
            for var, var_type in sorted(type_env.items(), key=lambda x: str(x[0]))
            if var_type.dim_sizes is not None and var_type.dim_sizes != []
        ]
    )


def render_function(func: Function, type_env: TypeEnv, ran_vectorization: bool) -> str:
    params = ", ".join(render_var(param.var, dict()) for param in func.parameters)
    shared_array_decls = indent(render_shared_array_decls(type_env), "    ")
    func_body = indent(render_statements(func.body, None), "    ")
    return (
        f"def {func.name}({params}):\n"
        + "    # Shared array declarations\n"
        + f"{shared_array_decls}\n"
        + "    # Function body\n"
        + f"{func_body}"
    )


def render_load_args(func: Function) -> str:
    ret = []
    program_args_index = 1
    for arg in func.parameters:
        var = render_var(arg.var, dict())
        party = arg.party_idx or 0
        dims = arg.var_type.dims
        if dims == 0:
            if arg.var_type.is_plaintext():
                ret.append(f"{var} = int(program.args[{program_args_index}])")
                program_args_index += 1
            else:
                ret.append(f"{var} = sint.get_input_from({party})")
        else:
            assert dims == 1
            ret.append(f"{var} = sint.Array(int(program.args[{program_args_index}]))")
            ret.append(f"{var}.input_from({party})")
            program_args_index += 1
    return "\n".join(ret)


def render_args(func: Function) -> str:
    return ", ".join(render_var(arg.var, dict()) for arg in func.parameters)


def render_application(
    func: Function, type_env: TypeEnv, params: dict[str, Any], ran_vectorization: bool
) -> None:
    func_rendered = render_function(func, type_env, ran_vectorization)
    load_args = render_load_args(func)
    args = render_args(func)
    app_rendered = (
        "from vectorization_library import *\n"
        + "\n"
        + "\n"
        + f"{func_rendered}\n"
        + "\n"
        + "\n"
        + "# Load arguments\n"
        + f"{load_args}\n"
        + "\n"
        + f"print_ln('OUTPUT %s', reveal_full({func.name}({args})))"
    )
    with open(params["out_dir"], "w") as file:
        file.write(app_rendered + "\n")
