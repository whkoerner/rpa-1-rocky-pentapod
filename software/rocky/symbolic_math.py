"""Bounded symbolic mathematics for Assistant V2.

User strings are never passed to sympy.sympify/parse_expr because those string
parsers may evaluate Python. We parse a small expression grammar with ast and
construct approved SymPy objects directly.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import re

import sympy as sp


class SymbolicMathError(ValueError):
    pass


_ALLOWED_FUNCTIONS = {
    "sqrt": sp.sqrt,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "exp": sp.exp,
    "log": sp.log,
}
_ALLOWED_CONSTANTS = {
    "pi": sp.pi,
    "e": sp.E,
}
_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
_MAX_NODES = 80
_MAX_OUTPUT = 4096
_MAX_INTEGER_ABS = 10**12
_MAX_POWER_ABS = 32


@dataclass
class _Budget:
    nodes: int = _MAX_NODES

    def use(self):
        self.nodes -= 1
        if self.nodes < 0:
            raise SymbolicMathError("symbolic expression is too complex")


def normalize_symbolic_text(text: str) -> str:
    if type(text) is not str:
        raise SymbolicMathError("symbolic expression must be a string")
    value = text.strip()
    if not value or len(value) > 256:
        raise SymbolicMathError("symbolic expression must be 1-256 characters")
    translations = str.maketrans({
        "×": "*",
        "÷": "/",
        "−": "-",
        "π": "pi",
        "²": "**2",
        "³": "**3",
    })
    value = value.translate(translations).replace("^", "**")
    # Common student notation only: 3x, 2pi, 3sin(x), and (x+1)2.
    # We deliberately do not implement a general implicit-multiplication parser.
    value = re.sub(r"(?<=\d)(?=[A-Za-z(])", "*", value)
    value = re.sub(r"(?<=\))(?=[A-Za-z0-9(])", "*", value)
    return value


def _number(value):
    if type(value) is int:
        if abs(value) > _MAX_INTEGER_ABS:
            raise SymbolicMathError("integer literal is outside safe bounds")
        return sp.Integer(value)
    if type(value) is float:
        if not (-1e100 <= value <= 1e100):
            raise SymbolicMathError("number literal is outside safe bounds")
        return sp.Rational(str(value))
    raise SymbolicMathError("unsupported numeric literal")


def _build(node: ast.AST, symbols: dict[str, sp.Symbol], budget: _Budget):
    budget.use()
    if isinstance(node, ast.Expression):
        return _build(node.body, symbols, budget)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return _number(node.value)
    if isinstance(node, ast.Name):
        name = node.id
        if name in _ALLOWED_CONSTANTS:
            return _ALLOWED_CONSTANTS[name]
        if not _IDENTIFIER.fullmatch(name) or name.startswith("_"):
            raise SymbolicMathError("invalid symbol name")
        return symbols.setdefault(name, sp.Symbol(name, real=True))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _build(node.operand, symbols, budget)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        left = _build(node.left, symbols, budget)
        right = _build(node.right, symbols, budget)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == 0:
                raise SymbolicMathError("division by zero")
            return left / right
        if isinstance(node.op, ast.Pow):
            if not right.is_number or not right.is_Integer:
                raise SymbolicMathError("power exponent must be an integer")
            exponent = int(right)
            if abs(exponent) > _MAX_POWER_ABS:
                raise SymbolicMathError("power exponent is outside safe bounds")
            if left == 0 and exponent < 0:
                raise SymbolicMathError("division by zero")
            return left ** exponent
        raise SymbolicMathError("operator is not allowed")
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _ALLOWED_FUNCTIONS
        and len(node.args) == 1
        and not node.keywords
    ):
        return _ALLOWED_FUNCTIONS[node.func.id](
            _build(node.args[0], symbols, budget)
        )
    raise SymbolicMathError("expression contains a forbidden construct")


def parse_symbolic_expression(text: str):
    normalized = normalize_symbolic_text(text)
    try:
        tree = ast.parse(normalized, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise SymbolicMathError("malformed symbolic expression") from exc
    symbols: dict[str, sp.Symbol] = {}
    expression = _build(tree, symbols, _Budget())
    if sp.count_ops(expression, visual=False) > 80:
        raise SymbolicMathError("symbolic expression is too complex")
    return expression, symbols


def _variable(name: object, symbols: dict[str, sp.Symbol]) -> sp.Symbol:
    if type(name) is not str or not _IDENTIFIER.fullmatch(name) or name.startswith("_"):
        raise SymbolicMathError("variable must be a simple identifier")
    return symbols.get(name) or sp.Symbol(name, real=True)


def _format(value) -> str:
    if isinstance(value, (list, tuple)):
        text = "[" + ", ".join(str(item) for item in value) + "]"
    else:
        text = str(value)
    if len(text) > _MAX_OUTPUT:
        raise SymbolicMathError("symbolic result exceeds safe output bounds")
    return text


def simplify_expression(expression: object) -> str:
    if type(expression) is not str:
        raise SymbolicMathError("expression must be a string")
    value, _ = parse_symbolic_expression(expression)
    return _format(sp.simplify(value))


def derivative(expression: object, variable: object = "x") -> str:
    if type(expression) is not str:
        raise SymbolicMathError("expression must be a string")
    value, symbols = parse_symbolic_expression(expression)
    symbol = _variable(variable, symbols)
    return _format(sp.diff(value, symbol))


def integral(expression: object, variable: object = "x") -> str:
    if type(expression) is not str:
        raise SymbolicMathError("expression must be a string")
    value, symbols = parse_symbolic_expression(expression)
    symbol = _variable(variable, symbols)
    result = sp.integrate(value, symbol)
    if isinstance(result, sp.Integral):
        raise SymbolicMathError("integral was not resolved exactly")
    return _format(result)


def solve_equation(equation: object, variable: object = "x") -> str:
    if type(equation) is not str:
        raise SymbolicMathError("equation must be a string")
    normalized = normalize_symbolic_text(equation)
    if normalized.count("=") != 1:
        raise SymbolicMathError("equation must contain exactly one equals sign")
    left_text, right_text = normalized.split("=", 1)
    left, left_symbols = parse_symbolic_expression(left_text)
    right, right_symbols = parse_symbolic_expression(right_text)
    symbols = {**left_symbols, **right_symbols}
    symbol = _variable(variable, symbols)
    if symbol not in (left - right).free_symbols:
        raise SymbolicMathError("requested variable is not present in the equation")
    if len((left - right).free_symbols) > 4:
        raise SymbolicMathError("equation has too many variables")
    result = sp.solve(sp.Eq(left, right), symbol)
    if len(result) > 16:
        raise SymbolicMathError("equation has too many solutions")
    return _format(result)


def explain_symbolic_operation(
    operation: object,
    expression: object,
    variable: object = "x",
) -> str:
    """Return deterministic, study-ready steps tied to the exact symbolic result."""
    result = symbolic_operation(operation, expression, variable)
    if operation == "solve":
        normalized = normalize_symbolic_text(expression)
        left_text, right_text = normalized.split("=", 1)
        left, left_symbols = parse_symbolic_expression(left_text)
        right, right_symbols = parse_symbolic_expression(right_text)
        symbols = {**left_symbols, **right_symbols}
        symbol = _variable(variable, symbols)
        solutions = sp.solve(sp.Eq(left, right), symbol)
        lines = [
            f"Equation: {left} = {right}",
            f"Solve for {symbol}.",
            f"Exact solution: {result}",
        ]
        for solution in solutions[:4]:
            checked_left = sp.simplify(left.subs(symbol, solution))
            checked_right = sp.simplify(right.subs(symbol, solution))
            lines.append(
                f"Check {symbol} = {solution}: left = {checked_left}, right = {checked_right}."
            )
        return "\n".join(lines)
    value, symbols = parse_symbolic_expression(expression)
    symbol = _variable(variable, symbols)
    if operation == "derivative":
        lines = [
            f"Expression: {value}",
            f"Differentiate with respect to {symbol}.",
        ]
        terms = value.as_ordered_terms() if isinstance(value, sp.Add) else [value]
        if len(terms) <= 12:
            for term in terms:
                lines.append(f"d/d{symbol}({term}) = {sp.diff(term, symbol)}")
        lines.append(f"Result: {result}")
        return "\n".join(lines)
    if operation == "integral":
        lines = [
            f"Expression: {value}",
            f"Integrate with respect to {symbol}.",
        ]
        terms = value.as_ordered_terms() if isinstance(value, sp.Add) else [value]
        if len(terms) <= 12:
            for term in terms:
                part = sp.integrate(term, symbol)
                if isinstance(part, sp.Integral):
                    raise SymbolicMathError("integral step was not resolved exactly")
                lines.append(f"∫({term}) d{symbol} = {part}")
        lines.append(f"Antiderivative: {result} + C")
        return "\n".join(lines)
    if operation == "simplify":
        return "\n".join(
            (
                f"Expression: {value}",
                "Apply exact algebraic simplification.",
                f"Result: {result}",
            )
        )
    raise SymbolicMathError("unsupported symbolic operation")


def symbolic_operation(
    operation: object,
    expression: object,
    variable: object = "x",
) -> str:
    if type(operation) is not str:
        raise SymbolicMathError("operation must be a string")
    if operation == "simplify":
        return simplify_expression(expression)
    if operation == "derivative":
        return derivative(expression, variable)
    if operation == "integral":
        return integral(expression, variable)
    if operation == "solve":
        return solve_equation(expression, variable)
    raise SymbolicMathError("unsupported symbolic operation")


_SYMBOLIC_PROMPTS = (
    (
        re.compile(
            r"^(?:(?:explain\s+how\s+to\s+find|find|calculate|what\s+is)\s+)?(?:the\s+)?(?:derivative\s+of|differentiate)\s+(.+?)(?:\s+with\s+respect\s+to\s+([A-Za-z][A-Za-z0-9_]*))?(?:\s+and\s+explain(?:\s+the\s+steps)?)?\s*[?!.]*$",
            re.I,
        ),
        "derivative",
    ),
    (
        re.compile(
            r"^(?:(?:explain\s+how\s+to\s+find|find|calculate|what\s+is)\s+)?(?:the\s+)?(?:integral\s+of|integrate)\s+(.+?)(?:\s+with\s+respect\s+to\s+([A-Za-z][A-Za-z0-9_]*))?(?:\s+and\s+explain(?:\s+the\s+steps)?)?\s*[?!.]*$",
            re.I,
        ),
        "integral",
    ),
    (
        re.compile(
            r"^solve\s+(.+?=.+?)(?:\s+for\s+([A-Za-z][A-Za-z0-9_]*))?(?:\s+and\s+explain(?:\s+the\s+steps)?)?\s*[?!.]*$",
            re.I,
        ),
        "solve",
    ),
    (
        re.compile(
            r"^simplify\s+(.+?)(?:\s+and\s+explain(?:\s+the\s+steps)?)?\s*[?!.]*$",
            re.I,
        ),
        "simplify",
    ),
)


def detect_symbolic_request(text: str):
    if type(text) is not str:
        return None
    value = " ".join(text.strip().split())
    for pattern, operation in _SYMBOLIC_PROMPTS:
        match = pattern.fullmatch(value)
        if match:
            expression = match.group(1).strip()
            variable = (
                match.group(2).strip()
                if match.lastindex and match.lastindex >= 2 and match.group(2)
                else "x"
            )
            return {
                "operation": operation,
                "expression": expression,
                "variable": variable,
            }
    return None
