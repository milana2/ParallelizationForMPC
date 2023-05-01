from textwrap import indent
from typing import Any, Optional, Union
import dataclasses as dc

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
from ...type_analysis import TypeEnv, Constant, DataType


UpdatelessAssignRHS = Union[
    Atom, Subscript, BinOp, UnaryOp, List, Tuple, Mux, LiftExpr, DropDim
]


VALID_PROTOCOLS = [
    #"mascot",
    # "lowgear",
    # "highgear",
    # "spdz2k",
    # "tiny",
    # "tinier",
    #"semi-bmr",
    # "cowgear",
    # "chaigear",
    #"semi",
    #"hemi",
    #"temi",
    "soho",
    #"semi2k",
    "semi-bin",
    # "yao-gc",
    # "yao-bmr",
    # "shamir",
    # "rep3",
    # "ps",
    # "sy",
    # "brain",
    # "ccd",
    # "atlas",
    # "rep4",
    # "dealer",
]


def render_var(var: Var, var_mappings: dict[Var, str]) -> str:
    try:
        return var_mappings[var]
    except KeyError:
        return str(var).replace("!", "_")


def render_vec_indices(v: VectorizedAccess, var_mappings: dict[Var, str]) -> str:
    return (
        "["
        + ", ".join(
            [
                "None" if vectorized else render_var(var, var_mappings)
                for vectorized, var in zip(v.vectorized_dims, v.idx_vars)
            ]
        )
        + "]"
    )


def render_array_shape(shape: tuple[LoopBound, ...], simdify: bool = False) -> str:
    return (
        "["
        + ", ".join([render_atom(dim_size, False, dict(), simdify) for dim_size in shape])
        + "]"
    )


def normalize_vectorized_access(v: VectorizedAccess) -> VectorizedAccess:
    array = v.array
    while isinstance(array, VectorizedAccess):
        if all(array.vectorized_dims):
            array = array.array
        else:
            array = Var("(TODO: fix this case)")
    return dc.replace(v, array=array)


def render_vectorized_access(v: VectorizedAccess, var_mappings: dict[Var, str], simdify: bool = False) -> str:
    v = normalize_vectorized_access(v)
    array = render_var(v.array, var_mappings)
    shape = render_array_shape(v.dim_sizes)
    indices = render_vec_indices(v, var_mappings)
    if simdify:
        return f"_v.vectorized_access_simd({array}, {shape}, {indices})"
    else:
        return f"_v.vectorized_access({array}, {shape}, {indices})"
    

def render_vectorized_assign(lhs: VectorizedAccess, rhs: UpdatelessAssignRHS) -> str:
    lhs = normalize_vectorized_access(lhs)
    array = render_var(lhs.array, dict())
    value = render_assign_rhs(rhs, dict())
    # TODO: Ana added these two lines.
    if isinstance(rhs, LiftExpr): 
        return f"{array} = {value}"
    shape = render_array_shape(lhs.dim_sizes)
    indices = render_vec_indices(lhs, dict())
    return f"_v.vectorized_assign({array}, {shape}, {indices}, {value})"


def render_constant(c: Constant, make_shared: bool) -> str:
    v = c.value
    if make_shared:
        if isinstance(v, bool):
            return f"_v.sbool({v})"
        elif isinstance(v, int):
            return f"sint({v})"
        else:
            assert_never(v)
    else:
        return str(v)


def render_atom(atom: Atom, make_shared: bool, var_mappings: dict[Var, str], simdify: bool = False) -> str:
    if isinstance(atom, Var):
        return render_var(atom, var_mappings)
    elif isinstance(atom, Constant):
        return render_constant(atom, make_shared)
    elif isinstance(atom, VectorizedAccess):
        return render_vectorized_access(atom, var_mappings, simdify)
    else:
        assert_never(atom)


def render_bin_op(left: str, op: BinOpKind, right: str) -> str:
    if op == BinOpKind.AND:
        return f"{left}.bit_and({right})"
    elif op == BinOpKind.OR:
        return f"OR({left}, {right})"
    else:
        return f"({left} {op} {right})"


def render_unary_op_kind(op: UnaryOpKind, operand: str) -> str:
    if op is UnaryOpKind.NEGATE:
        return f"-{operand}"
    elif op is UnaryOpKind.NOT:
        return f"{operand}.bit_not()"
    else:
        assert_never(op)


def render_subscript_index(index: SubscriptIndex, var_mappings: dict[Var, str]) -> str:
    if isinstance(index, (Var, Constant)):
        return render_atom(index, False, var_mappings)
    elif isinstance(index, SubscriptIndexBinOp):
        left = render_subscript_index(index.left, var_mappings)
        right = render_subscript_index(index.right, var_mappings)
        return render_bin_op(left, index.operator, right)
    elif isinstance(index, SubscriptIndexUnaryOp):
        operand = render_subscript_index(index.operand, var_mappings)
        expr = render_unary_op_kind(index.operator, operand)
        return f"({expr})"
    else:
        assert_never(index)


def render_lift_expr(lift: LiftExpr) -> str:
    assert not isinstance(lift.expr, (Update, VectorizedUpdate))
    expr = render_assign_rhs(
        lift.expr,
        {var: f"indices[{index}]" for index, (var, _) in enumerate(lift.dims)},
    )
    dim_sizes = ", ".join(render_atom(size, False, dict()) for (_, size) in lift.dims)
    #return f"_v.lift(lambda indices: {expr}, [{dim_sizes}]).get_vector()"
    return f"_v.lift(lambda indices: {expr}, [{dim_sizes}])" 


def render_assign_rhs(
    arhs: UpdatelessAssignRHS,
    var_mappings: dict[Var, str],
    simdify: bool = False
) -> str:
    if isinstance(arhs, BinOp):
        left = render_assign_rhs(arhs.left, var_mappings,simdify=True)
        right = render_assign_rhs(arhs.right, var_mappings,simdify=True)
        return render_bin_op(left, arhs.operator, right)
    elif isinstance(arhs, (Var, Constant, VectorizedAccess)):
        return render_atom(arhs, True, var_mappings, simdify)
    elif isinstance(arhs, List):
        items_list = [render_atom(item, True, var_mappings) for item in arhs.items]
        items = ", ".join(items_list)
        return f"[{items}]"
    elif isinstance(arhs, Tuple):
        items = "".join(
            render_atom(item, True, var_mappings, simdify) + "," for item in arhs.items
        )
        return f"({items})"
    elif isinstance(arhs, Mux):
        condition = render_assign_rhs(arhs.condition, var_mappings)
        true_value = render_assign_rhs(arhs.true_value, var_mappings)
        false_value = render_assign_rhs(arhs.false_value, var_mappings)
        return f"{condition}.if_else({true_value}, {false_value})"
    elif isinstance(arhs, UnaryOp):
        operand = render_assign_rhs(arhs.operand, var_mappings,simdify=True)
        expr = render_unary_op_kind(arhs.operator, operand)
        return f"({expr})"
    elif isinstance(arhs, Subscript):
        array = render_assign_rhs(arhs.array, var_mappings, simdify)
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
        shape = render_array_shape(arhs.dims)
        return f"_v.drop_dim({array}, {shape})"
    else:
        return assert_never(arhs)


def render_loop_exit_phi(loop: For) -> str:
    return "\n".join(
        render_statement(Assign(lhs=phi.lhs, rhs=phi.rhs_true), None)
        for phi in loop.body
        if isinstance(phi, Phi)
    )


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
        lhs = render_atom(stmt.lhs, False, dict())
        if isinstance(stmt.rhs, Update):
            array = render_var(stmt.rhs.array, dict())
            index = render_subscript_index(stmt.rhs.index, dict())
            value = render_atom(stmt.rhs.value, True, dict())
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
            # TODO: Cludgy fix for SPDZ vectorized MUX, 2 lines
            if isinstance(stmt.rhs,Mux):
                return render_iterative_mux(stmt.lhs, stmt.rhs)
            return render_vectorized_assign(stmt.lhs, stmt.rhs)
        else:
            rhs = render_assign_rhs(stmt.rhs, dict())
            return f"{lhs} = {rhs}"
    elif isinstance(stmt, For):
        counter = render_var(stmt.counter, dict())
        bound_low = render_atom(stmt.bound_low, False, dict())
        bound_high = render_atom(stmt.bound_high, False, dict())
        body = indent(render_statements(stmt.body, stmt), "    ")
        exit_phi = render_loop_exit_phi(stmt)
        return (
            f"for {counter} in range({bound_low}, {bound_high}):\n"
            + f"{body}\n"
            + "# Loop exit ϕ values\n"
            + exit_phi
        )
    elif isinstance(stmt, Return):
        value = render_var(stmt.value, dict())
        return f"return {value}"
    else:
        assert_never(stmt)


def render_statements(stmts: list[Statement], containing_loop: Optional[For]) -> str:
    return "\n".join(render_statement(stmt, containing_loop) for stmt in stmts)

#TODO: Check. Cludgy fix for SPDZ vectorized MUX (in binary)
def render_iterative_mux(lhs: VectorizedAccess, rhs: Mux):
    assert isinstance(rhs,Mux), f"Expected Mux rhs, found {type(rhs)}"
    lhs = normalize_vectorized_access(lhs)
    dest_array = render_var(lhs.array, dict())
    shape = render_array_shape(lhs.dim_sizes)
    indices = render_vec_indices(lhs, dict())
    # TODO: We need an assertions to make sure Vectorized accesses use same dimenstions and indices
    if isinstance(rhs.condition,VectorizedAccess):
       cond = render_var(normalize_vectorized_access(rhs.condition).array, dict())
    else:
       cond = render_assign_rhs(rhs.condition, dict())
    if isinstance(rhs.true_value,VectorizedAccess):   
       true_value = render_var(normalize_vectorized_access(rhs.true_value).array, dict())
    else: # rendering a constant or a variable
       true_value = render_assign_rhs(rhs.true_value, dict())
    if isinstance(rhs.false_value,VectorizedAccess):   
       false_value = render_var(normalize_vectorized_access(rhs.false_value).array, dict())
    else:
       false_value = render_assign_rhs(rhs.false_value, dict())
    return f"_v.iterative_mux({dest_array},{cond},{true_value},{false_value},{shape},{indices})"

def render_shared_array_decl(
    var: Var, datatype: Optional[DataType], dim_sizes: list[LoopBound]
) -> str:
    var_rendered = render_var(var, dict())
    size_rendered = " * ".join(
        [render_atom(dim_size, False, dict()) for dim_size in dim_sizes]
    )

    return f"{var_rendered} = [None] * ({size_rendered})"


def render_shared_array_decls(type_env: TypeEnv) -> str:
    return "\n".join(
        [
            render_shared_array_decl(var, var_type.datatype, var_type.dim_sizes)
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
                #program_args_index += 1
            else:
                ret.append(f"{var} = sint.get_input_from({party})")
            program_args_index += 1     
        else:
            assert dims == 1
            if arg.var_type.is_plaintext():
                ret.append(f"{var} = int(program.args[{program_args_index}])")
            else:
                ret.append(f"{var} = sint.Array(int(program.args[{program_args_index}]))")
                ret.append(f"{var}.input_from({party})")
            program_args_index += 1
    return "\n".join(ret)


def render_default_arg(arg: Parameter) -> str:
    var = render_var(arg.var, dict())
    dims = arg.var_type.dims
    value = arg.default_values[0]
    if dims == 0:
        if arg.var_type.is_plaintext():
            return f"{var} = {value}"
        else:
            return f"{var} = sint({value})"
    else:
        assert dims == 1
        return f"{var} = {value}; {var} = _v.lift(lambda indices: {var}[indices[0]], [len({var})])"


def render_default_args(func: Function) -> str:
    return "\n".join(render_default_arg(arg) for arg in func.parameters)


def render_set_args(func: Function) -> str:
    has_defaults = all(len(arg.default_values) >= 1 for arg in func.parameters)
    if has_defaults:
        return "\n".join(
            [
                "try:",
                "    # Load input arguments",
                indent(render_load_args(func), "    "),
                "except:",
                "    # Use default arguments",
                indent(render_default_args(func), "    "),
            ]
        )
    else:
        return render_load_args(func)


def render_args(func: Function) -> str:
    return ", ".join(render_var(arg.var, dict()) for arg in func.parameters)


def render_application(
    func: Function, type_env: TypeEnv, params: dict[str, Any], ran_vectorization: bool
) -> None:
    func_rendered = render_function(func, type_env, ran_vectorization)
    set_args = render_set_args(func)
    args = render_args(func)
    app_rendered = (
        "from vectorization_library import VectorizationLibrary\n"
        + "_v = VectorizationLibrary(globals())\n"
        + "from Compiler.util import OR\n"
        + "\n"
        + "\n"
        + f"{func_rendered}\n"
        + "\n"
        + "\n"
        + "# Set arguments\n"
        + f"{set_args}\n"
        + "\n"
        + f"_v.mpc_print_result({func.name}({args}))"
    )
    with open(params["out_dir"], "w") as file:
        file.write(app_rendered + "\n")
