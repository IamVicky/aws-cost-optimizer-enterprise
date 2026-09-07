"""Restricted expression evaluator for config-defined waste/guardrail rules.

Service YAML files embed small Python-like expressions (waste conditions,
savings formulas, numeric guardrail conditions) that must be evaluated
against a row of metrics without giving config authors arbitrary code
execution. This walks the ast and only permits a safe subset of nodes.
"""
import ast
import operator

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_COMPARE = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

_ALLOWED_UNARY = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_ALLOWED_CALLS = {
    "max": max,
    "min": min,
    "int": int,
    "round": round,
    "abs": abs,
}


class UnsafeExpressionError(ValueError):
    pass


def _eval_node(node, variables: dict):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variables)
    if isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, bool, str)) and node.value is not None:
            raise UnsafeExpressionError(f"Unsupported constant: {node.value!r}")
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise UnsafeExpressionError(f"Unknown variable: {node.id}")
        return variables[node.id]
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, variables) for v in node.values]
        if isinstance(node.op, ast.And):
            result = True
            for v in values:
                result = result and v
            return result
        if isinstance(node.op, ast.Or):
            result = False
            for v in values:
                result = result or v
            return result
        raise UnsafeExpressionError(f"Unsupported boolean operator: {node.op}")
    if isinstance(node, ast.UnaryOp):
        op_fn = _ALLOWED_UNARY.get(type(node.op))
        if op_fn is None:
            raise UnsafeExpressionError(f"Unsupported unary operator: {node.op}")
        return op_fn(_eval_node(node.operand, variables))
    if isinstance(node, ast.BinOp):
        op_fn = _ALLOWED_BINOPS.get(type(node.op))
        if op_fn is None:
            raise UnsafeExpressionError(f"Unsupported binary operator: {node.op}")
        return op_fn(_eval_node(node.left, variables), _eval_node(node.right, variables))
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, variables)
        for op, comparator in zip(node.ops, node.comparators):
            op_fn = _ALLOWED_COMPARE.get(type(op))
            if op_fn is None:
                raise UnsafeExpressionError(f"Unsupported comparison operator: {op}")
            right = _eval_node(comparator, variables)
            if not op_fn(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_CALLS:
            raise UnsafeExpressionError(f"Unsupported function call: {ast.dump(node.func)}")
        if node.keywords:
            raise UnsafeExpressionError("Keyword arguments are not supported")
        args = [_eval_node(a, variables) for a in node.args]
        return _ALLOWED_CALLS[node.func.id](*args)
    raise UnsafeExpressionError(f"Unsupported expression node: {type(node).__name__}")


def safe_eval(expr: str, variables: dict):
    """Evaluates a restricted Python expression against a dict of variables.

    Supports: comparisons, boolean and/or/not, arithmetic (+ - * / % **),
    numeric/string/bool literals, and variable lookups. Anything else
    (calls, attribute access, subscripts, imports, comprehensions, ...)
    raises UnsafeExpressionError.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise UnsafeExpressionError(f"Invalid expression syntax: {expr!r}") from e
    return _eval_node(tree, variables)
