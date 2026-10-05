"""Deterministic Assistant V2 software tools.

No eval/exec, filesystem, shell, network, hardware handle, or arbitrary import is
available through this registry.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
import math
import re
from typing import Callable

from brain.constitution import ActionDomain, AuthorityRequest, RockySafetyConstitution

from .assistant_contracts import ToolCall, ToolResult


class ToolExecutionError(ValueError):
    pass


Number = Fraction | Decimal


def _as_decimal(value: Number) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(value.numerator) / Decimal(value.denominator)


def _magnitude_ok(value: Number) -> bool:
    decimal = _as_decimal(value)
    return decimal.is_finite() and abs(decimal) <= Decimal("1e100")


def _binary(left: Number, right: Number, op: ast.operator) -> Number:
    if isinstance(op, ast.Div) and right == 0:
        raise ToolExecutionError("division by zero")
    if isinstance(op, ast.Add):
        value = left + right if type(left) is type(right) else _as_decimal(left) + _as_decimal(right)
    elif isinstance(op, ast.Sub):
        value = left - right if type(left) is type(right) else _as_decimal(left) - _as_decimal(right)
    elif isinstance(op, ast.Mult):
        value = left * right if type(left) is type(right) else _as_decimal(left) * _as_decimal(right)
    elif isinstance(op, ast.Div):
        if isinstance(left, Fraction) and isinstance(right, Fraction):
            value = left / right
        else:
            value = _as_decimal(left) / _as_decimal(right)
    elif isinstance(op, ast.Pow):
        exponent_decimal = _as_decimal(right)
        if exponent_decimal != exponent_decimal.to_integral_value():
            raise ToolExecutionError("power exponent must be an integer")
        exponent = int(exponent_decimal)
        if abs(exponent) > 32:
            raise ToolExecutionError("power exponent is outside safe bounds")
        if left == 0 and exponent < 0:
            raise ToolExecutionError("division by zero")
        value = left ** exponent
    elif isinstance(op, ast.Mod):
        if right == 0:
            raise ToolExecutionError("division by zero")
        value = left % right if type(left) is type(right) else _as_decimal(left) % _as_decimal(right)
    else:
        raise ToolExecutionError("operator is not allowed")
    if not _magnitude_ok(value):
        raise ToolExecutionError("result magnitude is outside safe bounds")
    return value


def _sqrt(value: Number) -> Number:
    if value < 0:
        raise ToolExecutionError("square root of negative number")
    if isinstance(value, Fraction):
        n = math.isqrt(value.numerator)
        d = math.isqrt(value.denominator)
        if n * n == value.numerator and d * d == value.denominator:
            return Fraction(n, d)
    with localcontext() as ctx:
        ctx.prec = 28
        return _as_decimal(value).sqrt()


def _eval_math(node: ast.AST, *, budget: list[int]) -> Number:
    budget[0] -= 1
    if budget[0] < 0:
        raise ToolExecutionError("expression is too complex")
    if isinstance(node, ast.Expression):
        return _eval_math(node.body, budget=budget)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = Fraction(str(node.value))
        if not _magnitude_ok(value):
            raise ToolExecutionError("number magnitude is outside safe bounds")
        return value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_math(node.operand, budget=budget)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
        return _binary(
            _eval_math(node.left, budget=budget),
            _eval_math(node.right, budget=budget),
            node.op,
        )
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "sqrt"
        and len(node.args) == 1
        and not node.keywords
    ):
        return _sqrt(_eval_math(node.args[0], budget=budget))
    raise ToolExecutionError("expression contains a forbidden construct")


def _format_number(value: Number) -> str:
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        with localcontext() as ctx:
            ctx.prec = 16
            decimal = Decimal(value.numerator) / Decimal(value.denominator)
        return f"{value.numerator}/{value.denominator} (~{decimal.normalize()})"
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def calculate_expression(expression: str) -> str:
    if type(expression) is not str or not expression.strip() or len(expression) > 256:
        raise ToolExecutionError("expression must be 1-256 characters")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise ToolExecutionError("malformed expression") from exc
    value = _eval_math(tree, budget=[64])
    return _format_number(value)


_ARITHMETIC_PATTERNS = (
    (re.compile(r"^(?:what is|calculate)?\s*(-?\d+(?:\.\d+)?)\s+(?:times|x|multiplied by)\s+(-?\d+(?:\.\d+)?)\s*[?!.]*$", re.I), "*"),
    (re.compile(r"^(?:what is|calculate)?\s*(-?\d+(?:\.\d+)?)\s+(?:plus|added to)\s+(-?\d+(?:\.\d+)?)\s*[?!.]*$", re.I), "+"),
    (re.compile(r"^(?:what is|calculate)?\s*(-?\d+(?:\.\d+)?)\s+minus\s+(-?\d+(?:\.\d+)?)\s*[?!.]*$", re.I), "-"),
    (re.compile(r"^(?:what is|calculate)?\s*(-?\d+(?:\.\d+)?)\s+(?:divided by|over)\s+(-?\d+(?:\.\d+)?)\s*[?!.]*$", re.I), "/"),
)
_PERCENT_PATTERN = re.compile(
    r"^(?:what is|calculate)?\s*(-?\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+(-?\d+(?:\.\d+)?)\s*[?!.]*$",
    re.I,
)
_SYMBOLIC_PATTERN = re.compile(r"^(?:what is|calculate)?\s*([0-9.()+\-*/%\s]+)\s*[?!.]*$", re.I)


def detect_arithmetic_expression(text: str) -> str | None:
    if type(text) is not str:
        return None
    value = " ".join(text.strip().split())
    match = _PERCENT_PATTERN.fullmatch(value)
    if match:
        return f"({match.group(1)}/100)*({match.group(2)})"
    for pattern, operator in _ARITHMETIC_PATTERNS:
        match = pattern.fullmatch(value)
        if match:
            return f"({match.group(1)}){operator}({match.group(2)})"
    match = _SYMBOLIC_PATTERN.fullmatch(value)
    if match and any(ch in match.group(1) for ch in "+-*/%"):
        return match.group(1)
    return None


_UNIT_FACTORS: dict[str, tuple[str, Decimal]] = {
    "mm": ("length", Decimal("0.001")),
    "cm": ("length", Decimal("0.01")),
    "m": ("length", Decimal("1")),
    "km": ("length", Decimal("1000")),
    "in": ("length", Decimal("0.0254")),
    "ft": ("length", Decimal("0.3048")),
    "yd": ("length", Decimal("0.9144")),
    "mi": ("length", Decimal("1609.344")),
    "mg": ("mass", Decimal("0.001")),
    "g": ("mass", Decimal("1")),
    "kg": ("mass", Decimal("1000")),
    "oz": ("mass", Decimal("28.349523125")),
    "lb": ("mass", Decimal("453.59237")),
    "ms": ("time", Decimal("0.001")),
    "s": ("time", Decimal("1")),
    "min": ("time", Decimal("60")),
    "h": ("time", Decimal("3600")),
    "ml": ("volume", Decimal("0.001")),
    "l": ("volume", Decimal("1")),
    "cup": ("volume", Decimal("0.2365882365")),
}


def convert_units(value: object, from_unit: object, to_unit: object) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ToolExecutionError("invalid numeric value") from exc
    if not number.is_finite() or abs(number) > Decimal("1e100"):
        raise ToolExecutionError("numeric value is outside safe bounds")
    if type(from_unit) is not str or type(to_unit) is not str:
        raise ToolExecutionError("units must be strings")
    source = from_unit.strip().lower()
    target = to_unit.strip().lower()

    if source in {"c", "f", "k"} or target in {"c", "f", "k"}:
        if source not in {"c", "f", "k"} or target not in {"c", "f", "k"}:
            raise ToolExecutionError("incompatible units")
        kelvin = (
            number + Decimal("273.15")
            if source == "c"
            else (number - Decimal("32")) * Decimal(5) / Decimal(9) + Decimal("273.15")
            if source == "f"
            else number
        )
        converted = (
            kelvin - Decimal("273.15")
            if target == "c"
            else (kelvin - Decimal("273.15")) * Decimal(9) / Decimal(5) + Decimal("32")
            if target == "f"
            else kelvin
        )
    else:
        if source not in _UNIT_FACTORS or target not in _UNIT_FACTORS:
            raise ToolExecutionError("unsupported unit")
        source_kind, source_factor = _UNIT_FACTORS[source]
        target_kind, target_factor = _UNIT_FACTORS[target]
        if source_kind != target_kind:
            raise ToolExecutionError("incompatible units")
        converted = number * source_factor / target_factor
    return _format_number(converted)


def date_difference(start: object, end: object) -> str:
    if type(start) is not str or type(end) is not str:
        raise ToolExecutionError("dates must be ISO YYYY-MM-DD strings")
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError as exc:
        raise ToolExecutionError("dates must be valid ISO YYYY-MM-DD") from exc
    return str((end_date - start_date).days)


@dataclass(frozen=True)
class AssistantToolRegistry:
    constitution: RockySafetyConstitution = RockySafetyConstitution()

    def names(self) -> tuple[str, ...]:
        return ("calculator", "date_difference", "unit_convert")

    def execute(self, call: ToolCall) -> ToolResult:
        decision = self.constitution.validate_authority_request(
            AuthorityRequest(call.name, ActionDomain.SOFTWARE, requested_by_model=True)
        )
        if not decision.allowed:
            return ToolResult(call.call_id, call.name, False, error=decision.code)
        if call.name not in self.names():
            return ToolResult(call.call_id, call.name, False, error="TOOL_NOT_ALLOWED")
        try:
            if call.name == "calculator":
                if set(call.arguments) != {"expression"}:
                    raise ToolExecutionError("calculator requires exactly expression")
                output = calculate_expression(call.arguments["expression"])
            elif call.name == "unit_convert":
                if set(call.arguments) != {"value", "from_unit", "to_unit"}:
                    raise ToolExecutionError(
                        "unit_convert requires exactly value, from_unit, to_unit"
                    )
                output = convert_units(
                    call.arguments["value"],
                    call.arguments["from_unit"],
                    call.arguments["to_unit"],
                )
            else:
                if set(call.arguments) != {"start", "end"}:
                    raise ToolExecutionError(
                        "date_difference requires exactly start and end"
                    )
                output = date_difference(
                    call.arguments["start"], call.arguments["end"]
                )
            return ToolResult(call.call_id, call.name, True, output=output)
        except (ToolExecutionError, ZeroDivisionError, OverflowError) as exc:
            return ToolResult(
                call.call_id,
                call.name,
                False,
                error=f"{type(exc).__name__}: {exc}",
            )
