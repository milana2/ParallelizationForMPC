from .type_analysis import type_check
from .dep_graph import DepGraph
from .loop_linear_code import (
    Function,
    Statement,
    Assign,
    TypeEnv,
    Phi,
    For,
    Return,
    VectorizedAccess,
    Constant,
    Mux,
    VectorizedUpdate,
    Subscript,
    Update
)
from .tac_cfg import LiftExpr, DropDim,BinOp,Tuple,UnaryOp,Var

from typing import Any,Optional,Union,Sequence
import dataclasses as dc


def _check_and_modify_rhs(
    stmt: Statement,
    dag:dict[str, Any],
    changes: dict[str, Any],
) -> Optional[Statement]:
    
    if not isinstance(stmt,(Return)) and (hasattr(stmt,'rhs') and str(stmt.rhs) in dag):
        if isinstance(stmt.rhs,DropDim)  and isinstance(stmt.rhs.array,VectorizedAccess):
            changes[str(stmt.lhs.array)] = dag[str(stmt.rhs)].array
        if isinstance(stmt.rhs,LiftExpr):
            changes[str(stmt.lhs.array)] = dag[str(stmt.rhs)].array
        if isinstance(stmt.rhs,BinOp) and isinstance(stmt.lhs,VectorizedAccess):
            changes[str(stmt.lhs.array)] = dag[str(stmt.rhs)].array
        if isinstance(stmt.rhs,Tuple) and isinstance(stmt.lhs,VectorizedAccess):
            changes[str(stmt.lhs.array)] = dag[str(stmt.rhs)].array
        if isinstance(stmt.rhs,Mux) and isinstance(stmt.lhs,VectorizedAccess):
            changes[str(stmt.lhs.array)] = dag[str(stmt.rhs)].array
        if isinstance(stmt.rhs,VectorizedUpdate):
            changes[str(stmt.lhs.array)] = dag[str(stmt.rhs)].array
        if isinstance(stmt.rhs,UnaryOp) and isinstance(stmt.lhs,VectorizedAccess):
            changes[str(stmt.lhs.array)] = dag[str(stmt.rhs)].array
        if isinstance(stmt.rhs,Subscript) or isinstance(stmt.rhs,Update):
            changes[str(stmt.lhs.array)] = dag[str(stmt.rhs)].array

        dag[str(stmt.lhs)] = dag[str(stmt.rhs)]
        return None
    elif isinstance(stmt,Phi) and str(stmt).split(" = ")[1] in dag:
        stmt_splits = str(stmt).split(" = ")
        if isinstance(stmt.lhs,VectorizedAccess) and hasattr(dag[stmt_splits[1]],'array'):
            changes[stmt_splits[0]] = getattr(dag[stmt_splits[1]], 'array', None)
            if changes[stmt_splits[0]] == None:
                del changes[stmt_splits[0]]
            # dag[stmt_splits[0]] = str(stmt).split(" = ")[1]
        return None
    else:
        if isinstance(stmt,For):
            return None
        elif isinstance(stmt,Phi):
            if isinstance(stmt.rhs_true,VectorizedAccess) and str(stmt.rhs_true.array) in changes:
                stmt.rhs_true.array = changes[str(stmt.rhs_true.array)]
            if isinstance(stmt.rhs_false,VectorizedAccess) and str(stmt.rhs_false.array) in changes:
                stmt.rhs_false.array = changes[str(stmt.rhs_false.array)]

            if str(stmt.rhs_true) in dag:
                stmt.rhs_true = dag[str(stmt.rhs_true)]
            if str(stmt.rhs_false) in dag:
                stmt.rhs_false = dag[str(stmt.rhs_false)]    
            
            if str(stmt).split(" = ")[1] in dag:
                dag[str(stmt.lhs)] = str(stmt).split(" = ")[1]
                return None
            return stmt
        elif isinstance(stmt,Return):
            if stmt.value in dag:
                stmt.value = dag[str(stmt.value)]
            return stmt
        elif isinstance(stmt.rhs,Constant):
            return stmt
        elif isinstance(stmt.rhs,LiftExpr):
            if  isinstance(stmt.rhs,VectorizedAccess) and str(stmt.rhs.expr.array) in changes:
                stmt.rhs.expr.array = changes[str(stmt.rhs.expr.array)]

            if str(stmt.rhs.expr) in dag:
                stmt.rhs.expr = dag[str(stmt.rhs.expr)]
            
            dag[str(stmt.rhs)] = stmt.lhs
            if str(stmt.rhs.expr) in dag:
                dag[str(stmt.lhs)] = dag[str(stmt.rhs.expr)]
                return None
            return stmt
        elif isinstance(stmt.rhs,DropDim):
            if isinstance(stmt.lhs,VectorizedAccess)  and str(stmt.rhs.array) in changes:
                stmt.rhs.array = changes[str(stmt.rhs.array)]
            
            dag[str(stmt.rhs)] = stmt.lhs
            return stmt
        elif isinstance(stmt.rhs,BinOp):
            if isinstance(stmt.rhs.left,VectorizedAccess)  and str(stmt.rhs.left.array) in changes:
                stmt.rhs.left.array = changes[str(stmt.rhs.left.array)]
            if isinstance(stmt.rhs.right,VectorizedAccess)  and str(stmt.rhs.right.array) in changes:
                stmt.rhs.right.array = changes[str(stmt.rhs.right.array)]

            if str(stmt.rhs.left) in dag:
                stmt.rhs.left = dag[str(stmt.rhs.left)]
            if str(stmt.rhs.right) in dag:
                stmt.rhs.right = dag[str(stmt.rhs.right)]    
            
            if str(stmt.rhs) in dag:
                dag[str(stmt.lhs)] = dag[str(stmt.rhs)]
                return None
            return stmt
        elif isinstance(stmt.rhs,Tuple):
            for i in range(len(stmt.rhs.items)):
                if isinstance(stmt.rhs.items[i],VectorizedAccess) and str(stmt.rhs.items[i]) in changes:
                    stmt.rhs.items[i].array = changes[str(stmt.rhs.items[i].array)]
                if str(stmt.rhs.items[i]) in dag:
                    stmt.rhs.items[i] = dag[str(stmt.rhs.items[i])]

            if str(stmt.rhs) in dag:
                dag[str(stmt.lhs)] = dag[str(stmt.rhs)]
                return None
            return stmt
        elif isinstance(stmt.rhs,Mux):
            if isinstance(stmt.rhs.condition,VectorizedAccess) and str(stmt.rhs.condition.array) in changes:
                stmt.rhs.condition.array = changes[str(stmt.rhs.condition.array)]
            if isinstance(stmt.rhs.true_value,VectorizedAccess) and str(stmt.rhs.true_value.array) in changes:
                stmt.rhs.true_value.array = changes[str(stmt.rhs.true_value.array)]
            if isinstance(stmt.rhs.false_value,VectorizedAccess) and str(stmt.rhs.false_value.array) in changes:
                stmt.rhs.false_value.array = changes[str(stmt.rhs.false_value.array)]
            
            if str(stmt.rhs.condition) in dag:
                stmt.rhs.condition = dag[str(stmt.rhs.condition)]
            if str(stmt.rhs.true_value) in dag:
                stmt.rhs.true_value = dag[str(stmt.rhs.true_value)]   
            if str(stmt.rhs.false_value) in dag:
                stmt.rhs.false_value = dag[str(stmt.rhs.false_value)]    
            
            if str(stmt.rhs) in dag:
                dag[str(stmt.lhs)] = dag[str(stmt.rhs)]
                return None
            return stmt
        elif isinstance(stmt.rhs,VectorizedUpdate):
            if str(stmt.rhs.array) in changes:
                stmt.rhs.array = changes[str(stmt.rhs.array)]
            if str(stmt.rhs.value) in changes:
                stmt.rhs.value = changes[str(stmt.rhs.value)]
            
            if str(stmt.rhs) in dag:
                dag[str(stmt.lhs)] = dag[str(stmt.rhs)]
                return None
            return stmt
        elif isinstance(stmt.rhs,UnaryOp):
            if isinstance(stmt.lhs,VectorizedAccess) and str(stmt.rhs.operand.array) in changes:
                stmt.rhs.operand.array = changes[str(stmt.rhs.operand.array)]
            
            if str(stmt.rhs) in dag:
                dag[str(stmt.lhs)] = dag[str(stmt.rhs)]
                return None
            return stmt
        elif isinstance(stmt.rhs,Subscript) or isinstance(stmt.rhs,Update):
            if str(stmt.rhs.array) in changes:
                stmt.rhs.array = changes[str(stmt.rhs.array)]
            
            if str(stmt.rhs) in dag:
                dag[str(stmt.lhs)] = dag[str(stmt.rhs)]
                return None
            return stmt
    
    return None

def traverse_and_optimize(
    dag:dict[str, Any],
    changes: dict[str, Any],
    statements:list[Statement]
) -> list[Union[Statement,None]]:
    ret:list[Union[Statement,None]] = []
    for stmt in statements:
        if isinstance(stmt, For):
            stmt = dc.replace(stmt, body=traverse_and_optimize(dag,changes,stmt.body))
            ret.append(stmt)    
        else:
            updated_stmt = _check_and_modify_rhs(stmt,dag,changes)
            if updated_stmt != None:
                ret.append(updated_stmt)
    return ret

def common_subexpression_elimination(
    func: Function, dep_graph: DepGraph, type_env: TypeEnv
) -> tuple[Function, DepGraph, TypeEnv]:
    dag: dict[str, Any] = dict()
    changes: dict[str, Any] = dict()
    func = dc.replace(func, body=traverse_and_optimize(dag,changes,func.body))
    dep_graph = DepGraph(func)
    func, type_env = type_check(func, dep_graph)
    return func, dep_graph, type_env

