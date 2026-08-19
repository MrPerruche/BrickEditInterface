# AI may be evil but i don't have time to refactor (and fix) ExpressionWidget myself ngl. hate me lol


"""
number_channel.py
==================

A numeric "channel" input for editing values that will end up stored as
float32 (or int) in a file, while doing all math in Python's native
float64.

The module is split into two independent halves:

1. Pure logic (ChannelMode, ulp_distance32, blurred_format32,
   focused_format32, ChannelModel, FormulaChannelModel,
   define_global/undefine_global) - no Qt dependency at all except for
   the two QValidators, which only need QValidator itself, not any
   particular line-edit implementation.

2. Qt glue (NumberChannelEdit, FormulaChannelEdit below) - a minimal
   reference pair built directly on QLineEdit, for projects with no
   custom line-edit wrapper. If you do have one - especially a
   composition-based wrapper (a plain object holding the real QLineEdit
   as a *child*, rather than subclassing it) - see channel_widgets.py
   instead, which is built against exactly that shape.

Design notes
------------
- The "true" value is always a plain Python float (float64), never
  silently snapped to its float32 cast. float32 is only used as a lens
  for *display* and for deciding how much precision that display can
  honestly claim.
- Unfocused display: round to `decimals` places. If that already loses
  meaningful float32 precision (checked in ULP space, not raw
  subtraction, so it behaves consistently across magnitudes), show it
  padded as-is so the trailing zeros signal "not exact". Otherwise keep
  coarsening (fewer decimals, then into the tens/hundreds/... place)
  for as long as that stays faithful, which is what gives you both
  "4.500 -> 4.5" and, for values whose magnitude exceeds float32's
  integer resolution, "123456789 -> 123456800" - zeros piling up
  instead of ever switching to scientific notation.
- That coarsening step is done with `decimal.Decimal`, not float
  `round()`. Past ~17 significant digits a float can no longer represent
  a "clean" round number at all, so rounding-and-reformatting a float
  directly prints its exact (and misleading) binary-to-decimal
  expansion instead of the intended zero-padded string. Decimal doesn't
  have that problem at any magnitude.
- Focused display: the shortest decimal string that round-trips exactly
  to the float32 cast of the value (numpy's Dragon4 algorithm via
  `np.format_float_positional(..., unique=True)`), which is the
  standard definition of "full float32 precision".
"""

from __future__ import annotations

import math
import warnings
import weakref
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from enum import Enum, auto
from typing import Optional

import numpy as np
from asteval import Interpreter

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QValidator

from ui.widgets import LineEdit


# ============================================================================
# 1. Pure logic - no Qt import above this line is used below this point.
# ============================================================================

class ChannelMode(Enum):
    FLOAT32 = auto()
    FLOAT64 = auto()
    INT = auto()


# float32 spans ~1.4e-45 (subnormal) to ~3.4e38, so a Decimal quantize
# might need digits on both sides of the point at once; the default
# context (28 significant digits) isn't enough. This comfortably covers
# the whole range with room to spare.
_DECIMAL_PREC = 200


def _f32_ordered_key(f) -> int:
    """Map a float32 bit pattern onto a monotonic integer line (sign
    included) so plain subtraction gives ULP distance. Standard trick
    used by ULP-comparison libraries."""
    bits = int(np.float32(f).view(np.uint32))
    if bits & 0x8000_0000:
        return -(bits & 0x7FFF_FFFF)
    return bits


def ulp_distance32(a, b) -> int:
    """Distance between `a` and `b`, in float32 ULPs. NaN vs NaN is 0
    distance (both "equally unrepresentable"); NaN vs a real number is
    treated as maximally far."""
    fa, fb = np.float32(a), np.float32(b)
    if np.isnan(fa) or np.isnan(fb):
        return 0 if (np.isnan(fa) and np.isnan(fb)) else 2**31
    return abs(_f32_ordered_key(fa) - _f32_ordered_key(fb))


def _round_decimal(d: Decimal, p: int) -> Decimal:
    """Round the *exact* decimal value `d` to `p` places after the point.
    `p` may be negative (round to the nearest ten/hundred/...). Exact
    decimal math, so this stays clean at any magnitude, unlike rounding
    a float and reformatting it."""
    quantum = Decimal(1).scaleb(-p)
    with localcontext() as ctx:
        ctx.prec = _DECIMAL_PREC
        return d.quantize(quantum, rounding=ROUND_HALF_EVEN)


def format_special(value: float) -> Optional[str]:
    """Returns the display string for nan/inf/-inf, or None for a normal
    finite value."""
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    return None


def blurred_format32(value: float, decimals: int, ulp_tolerance: int = 2,
                      min_precision: int = -45) -> str:
    """The 'unfocused' float32 display. See module docstring for the
    rules this implements."""
    special = format_special(value)
    if special is not None:
        return special

    f32 = np.float32(value)
    if f32 == 0:
        return "0"

    exact = Decimal(float(f32))  # exact: float32->float64->Decimal is lossless

    p = decimals
    candidate = _round_decimal(exact, p)
    if ulp_distance32(f32, float(candidate)) > ulp_tolerance:
        # Even `decimals` digits can't be trusted - show them anyway,
        # padded, so the trailing zeros make that visible.
        return format(candidate, "f")

    # It round-trips at `decimals`; keep coarsening for the cleanest
    # string that still round-trips within tolerance.
    best_p, best_val = p, candidate
    while p > min_precision:
        p -= 1
        cand = _round_decimal(exact, p)
        if ulp_distance32(f32, float(cand)) <= ulp_tolerance:
            best_p, best_val = p, cand
            if cand == 0:
                break  # further coarsening can only ever give 0 again
        else:
            break
    return format(best_val, "f")


def focused_format32(value: float) -> str:
    """The 'focused' display: full float32 precision, i.e. the shortest
    decimal string that round-trips exactly to this float32 value."""
    special = format_special(value)
    if special is not None:
        return special
    f32 = np.float32(value)
    return np.format_float_positional(f32, unique=True, trim="-")


# ----------------------------------------------------------------------
# Special-value text accepted while parsing, in addition to whatever
# asteval itself understands.
# ----------------------------------------------------------------------
_SPECIAL_INPUT = {
    "nan": math.nan, "-nan": math.nan,
    "inf": math.inf, "+inf": math.inf, "infinity": math.inf, "+infinity": math.inf,
    "-inf": -math.inf, "-infinity": -math.inf,
}


# ----------------------------------------------------------------------
# App-wide interpreter globals. Every ChannelModel gets its own private
# Interpreter (so one field's stray "y = 5" can never leak into another
# field's expressions) - but names registered here are pushed into every
# ChannelModel that exists now, and every one created later, so you can
# expose a shared, vetted set of math helpers to the whole app from one
# place. Use this instead of reaching into any particular model's
# ._aeval if you want the definition to be app-wide rather than local
# to one field.
# ----------------------------------------------------------------------
_global_defines: dict = {}
_live_models: "weakref.WeakSet" = weakref.WeakSet()


def define_global(name: str, value) -> None:
    """Expose a constant or callable to every ChannelModel/FormulaChannelModel
    in the app, present and future, e.g.:

        define_global('clamp01', lambda v: max(0.0, min(1.0, v)))
        define_global('deg2rad', math.radians)

    Safe in the sense that it only ever adds *names* to each model's own
    interpreter (each field's evaluation still runs in its own sandboxed
    Interpreter instance) - it doesn't share state or a symtable between
    fields, just the same definitions."""
    _global_defines[name] = value
    for model in list(_live_models):
        model.define(name, value)


def undefine_global(name: str) -> None:
    _global_defines.pop(name, None)
    for model in list(_live_models):
        model.undefine(name)


class ChannelModel:
    """Holds the configuration and behaviour for one numeric channel:
    mode, display precision, bounds, and whether nan/inf are allowed.
    Framework-agnostic - wire it into whatever QLineEdit you like."""

    def __init__(self, mode: ChannelMode = ChannelMode.FLOAT32, decimals: int = 6,
                 ulp_tolerance: int = 2, allow_nan: bool = True, allow_inf: bool = True,
                 minimum: Optional[float] = None, maximum: Optional[float] = None):
        self.mode = mode
        self.decimals = decimals
        self.ulp_tolerance = ulp_tolerance
        self.allow_nan = allow_nan
        self.allow_inf = allow_inf
        self.minimum = minimum
        self.maximum = maximum

        self._aeval = Interpreter(minimal=True, with_ifexp=True)
        self._aeval.symtable.update(pi=math.pi, e=math.e, inf=math.inf, nan=math.nan)
        self._aeval.symtable.update(_global_defines)
        # Names that survive reset() - the built-ins above, plus anything
        # added via define()/define_global(). A *set*, not a frozenset,
        # because define() grows it as you go.
        self._base_symtable_keys = set(self._aeval.symtable.keys())
        _live_models.add(self)

    # -- interpreter extension points ---------------------------------------

    def define(self, name: str, value) -> None:
        """Expose a constant or callable to every expression *this*
        model evaluates from now on, e.g. `model.define('clamp', fn)`.
        For something every channel in the app should have, use the
        module-level define_global() instead. Persists for the model's
        lifetime and survives reset()."""
        self._aeval.symtable[name] = value
        self._base_symtable_keys.add(name)

    def undefine(self, name: str) -> None:
        self._aeval.symtable.pop(name, None)
        self._base_symtable_keys.discard(name)

    def reset(self) -> None:
        """Drop anything left behind by a user expression that happened
        to assign a variable (e.g. typing 'y = 5' - see evaluate()'s
        docstring for why that's worth knowing about). Leaves pi/e/inf/nan
        and anything added via define()/define_global() in place."""
        for key in list(self._aeval.symtable.keys()):
            if key not in self._base_symtable_keys:
                del self._aeval.symtable[key]

    # -- expression evaluation -------------------------------------------------

    def evaluate(self, text: str) -> float:
        """Evaluate `text` and return a validated Python float (or raise
        ValueError with a human-readable reason)."""
        value = self._raw_evaluate(text)
        return self._coerce_and_validate(value)

    def _raw_evaluate(self, text: str) -> float:
        """Parse/run `text` and return a plain float, with no bounds/nan
        policy applied yet. Split out from evaluate() so formula-mode
        syntax checks (see FormulaChannelModel) can validate that an
        expression runs at all without also enforcing this channel's
        bounds against whatever placeholder value they probe it with."""
        text = text.strip()
        if not text:
            raise ValueError("empty expression")

        low = text.lower()
        if low in _SPECIAL_INPUT:
            return _SPECIAL_INPUT[low]

        self._aeval.error = []
        with warnings.catch_warnings():
            # asteval/numpy warn on e.g. sqrt(-1); we turn that into
            # nan via the normal float path instead of a console spew.
            warnings.simplefilter("ignore")
            result = self._aeval.eval(text, show_errors=False, raise_errors=False)
        if self._aeval.error:
            name, msg = self._aeval.error[0].get_error()
            raise ValueError(f"{name}: {msg.splitlines()[-1]}")
        if isinstance(result, bool) or result is None:
            raise ValueError("expression is not numeric")
        try:
            return float(result)
        except (TypeError, ValueError):
            raise ValueError("expression is not numeric")

    def evaluate_with(self, text: str, **variables) -> float:
        """Evaluate `text` with extra name->value bindings visible only
        for this call, e.g. `evaluate_with("2*x + 5", x=3)`. Bindings are
        removed again afterwards (restoring whatever those names held
        before, if anything) so they never leak into a later plain
        evaluate() call. Reuses the same Interpreter instance, so this is
        cheap enough to call in a loop while sweeping a variable over
        many values."""
        previous = {}
        added = []
        for name, val in variables.items():
            if name in self._aeval.symtable:
                previous[name] = self._aeval.symtable[name]
            else:
                added.append(name)
            self._aeval.symtable[name] = val
        try:
            return self.evaluate(text)
        finally:
            for name in added:
                del self._aeval.symtable[name]
            self._aeval.symtable.update(previous)

    def _coerce_and_validate(self, value: float) -> float:
        if math.isnan(value):
            if not self.allow_nan:
                raise ValueError("NaN is not allowed for this channel")
            return value
        if math.isinf(value):
            if not self.allow_inf:
                raise ValueError("Infinity is not allowed for this channel")
            return value
        if self.mode is ChannelMode.INT and not float(value).is_integer():
            raise ValueError("value must be a whole number")
        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"value must be >= {self.minimum}")
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"value must be <= {self.maximum}")
        return value

    def set_value(self, value: float) -> float:
        """Validate an externally-set value (e.g. loaded from file)."""
        return self._coerce_and_validate(float(value))

    # -- display -----------------------------------------------------------

    def format(self, value: float, focused: bool) -> str:
        if self.mode is ChannelMode.INT:
            special = format_special(value)
            return special if special is not None else str(int(value))
        if self.mode is ChannelMode.FLOAT64:
            special = format_special(value)
            if special is not None:
                return special
            return repr(float(value))
        # FLOAT32
        return focused_format32(value) if focused else blurred_format32(
            value, self.decimals, self.ulp_tolerance)


# ============================================================================
# 1b. Formula mode - the widget's content is an expression string like
#     "2*x + 5", evaluated on demand against caller-supplied variables,
#     rather than collapsing to one fixed number on commit.
# ============================================================================

class FormulaChannelModel:
    """Wraps a numeric ChannelModel to hold a *formula* instead of a
    value. The formula text is the authoritative content; evaluate_at()
    computes a concrete result against real variable values (still
    passing through the numeric model's mode/bounds/nan policy, since
    that's a property of each concrete result). validate_formula() is
    the cheaper check for "does this even parse and run", used to decide
    whether the field looks acceptable while the user is still typing -
    it deliberately does NOT enforce bounds, since bounds are a property
    of a specific evaluated result, not of the formula in the abstract.

    Shares its Interpreter (and therefore any define()'d names) with the
    numeric_model passed in, so anything you've exposed via
    numeric_model.define(...) is available here too.
    """

    def __init__(self, numeric_model: ChannelModel, variable_name: str = "x",
                 preview_value: float = 0.0):
        self.numeric_model = numeric_model
        self.variable_name = variable_name
        self.preview_value = preview_value

    def validate_formula(self, text: str) -> None:
        text = text.strip()
        if not text:
            raise ValueError("empty formula")
        # Deliberately calls the *raw* evaluator, bypassing bounds/nan
        # checks - see class docstring for why.
        previous_present = self.variable_name in self.numeric_model._aeval.symtable
        previous_value = self.numeric_model._aeval.symtable.get(self.variable_name)
        self.numeric_model._aeval.symtable[self.variable_name] = self.preview_value
        try:
            self.numeric_model._raw_evaluate(text)
        finally:
            if previous_present:
                self.numeric_model._aeval.symtable[self.variable_name] = previous_value
            else:
                del self.numeric_model._aeval.symtable[self.variable_name]

    def evaluate_at(self, text: str, **variables) -> float:
        """Evaluate the formula for real. If `variables` doesn't include
        this model's variable_name, nothing is bound under that name and
        the formula must supply it some other way (e.g. via define()).
        Raises ValueError - same as evaluate() - for anything that
        doesn't resolve to a number, or resolves to one outside this
        channel's mode/bounds/nan policy for *this* variable value."""
        return self.numeric_model.evaluate_with(text, **variables)

    def try_evaluate_at(self, text: str, **variables):
        """Like evaluate_at(), but returns (value, error_message) instead
        of raising - convenient for a batch loop where one bad object
        (wrong type, out of bounds, whatever) shouldn't blow up the
        whole run. error_message is None on success."""
        try:
            return self.evaluate_at(text, **variables), None
        except ValueError as e:
            return None, str(e)


# ============================================================================
# 2. Qt glue - reference implementation, adapt into your own LineEdit.
# ============================================================================

class ChannelValidator(QValidator):
    """Wraps ChannelModel.evaluate(). Never returns Invalid - anything
    that doesn't *yet* evaluate to an accepted number is Intermediate,
    so the user can keep typing an expression freely (e.g. "1/" while
    on the way to "1/3"). Wire the Intermediate/Acceptable distinction
    into your existing LineEdit's error-style / revert-on-focus-out
    handling."""

    def __init__(self, model: ChannelModel, parent=None):
        super().__init__(parent)
        self.model = model

    def validate(self, text: str, pos: int):
        if not text.strip():
            return QValidator.State.Intermediate, text, pos
        try:
            self.model.evaluate(text)
        except ValueError:
            return QValidator.State.Intermediate, text, pos
        return QValidator.State.Acceptable, text, pos


class NumberChannelEdit(LineEdit):
    """Shows the blurred float32 form while unfocused, full float32
    precision while focused, evaluates asteval expressions on commit,
    and silently reverts on anything that doesn't validate."""
 
    value_changed = Signal(object)  # emits float, or int for INT mode
 
    def __init__(self, mode: ChannelMode = ChannelMode.FLOAT32, decimals: int = 3,
                 parent=None, **model_kwargs):
        super().__init__(parent=parent)
        self.model = ChannelModel(mode=mode, decimals=decimals, **model_kwargs)
        self._value: float = 0.0
        self._dirty = False  # True only between a real keystroke and the next commit
        self.set_validator(ChannelValidator(self.model, self))
        self.qt_widget.installEventFilter(self)
        self.qt_widget.textEdited.connect(self._on_user_edit)
        self._refresh_display(focused=False)
 
    def value(self):
        return int(self._value) if self.model.mode is ChannelMode.INT else self._value
 
    def setValue(self, value) -> None:
        self._value = self.model.set_value(value)
        self._dirty = False
        self._refresh_display(focused=self.qt_widget.hasFocus())
        self.value_changed.emit(self.value())
 
    def get_text(self):
        # Overrides LineEdit.get_text(): that base implementation
        # answers "does the literal on-screen text currently validate",
        # which for this widget is the wrong question - live text while
        # typing an expression (e.g. "1/3") is not the canonical display
        # string ("0.333"/"0.3333333"). Always derive from the
        # committed value instead.
        return self.model.format(self._value, focused=self.qt_widget.hasFocus())
 
    # -- real Qt events, caught via event filter (see module docstring) --
 
    def eventFilter(self, obj, event) -> bool:
        if obj is self.qt_widget:
            et = event.type()
            if et == QEvent.Type.FocusIn:
                self._refresh_display(focused=True)
                self.select_all()
            elif et == QEvent.Type.FocusOut:
                self._commit()
            elif et == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._commit()
                    self.select_all()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self._dirty = False
                    self._refresh_display(focused=True)  # discard edits, keep focus
                    self.select_all()
                    return True
        return super().eventFilter(obj, event)
 
    def _on_user_edit(self, _text: str) -> None:
        self._dirty = True
 
    def _commit(self) -> None:
        if self._dirty:
            try:
                new_value = self.model.evaluate(self.get_true_text())
            except ValueError:
                pass  # silently revert to last valid value
            else:
                if new_value != self._value or math.isnan(new_value):
                    self._value = new_value
                    self.value_changed.emit(self.value())
            self._dirty = False
        self._refresh_display(focused=self.qt_widget.hasFocus())
 
    def _refresh_display(self, focused: bool) -> None:
        self.set_text(self.model.format(self._value, focused))



class FormulaChannelValidator(QValidator):
    """Like ChannelValidator, but checks formula syntax/runnability
    (against a placeholder variable value) rather than checking that the
    text is itself a plain number."""

    def __init__(self, formula_model: FormulaChannelModel, parent=None):
        super().__init__(parent)
        self.formula_model = formula_model

    def validate(self, text: str, pos: int):
        if not text.strip():
            return QValidator.State.Intermediate, text, pos
        try:
            self.formula_model.validate_formula(text)
        except ValueError:
            return QValidator.State.Intermediate, text, pos
        return QValidator.State.Acceptable, text, pos




class FormulaChannelEdit(LineEdit):
    """Formula-mode counterpart: the committed content is the formula
    string itself (e.g. "2*x + 5"), not a fixed number - there's no
    focused/unfocused precision distinction, since there's no single
    value to blur. Call evaluate_at(**variables) to compute a concrete
    result for a specific case (e.g. one object in a batch edit)."""
 
    formula_changed = Signal(str)
 
    def __init__(self, mode: ChannelMode = ChannelMode.FLOAT32, variable_name: str = "x",
                 preview_value: float = 0.0, parent=None, **model_kwargs):
        super().__init__(parent=parent)
        self.numeric_model = ChannelModel(mode=mode, **model_kwargs)
        self.model = FormulaChannelModel(self.numeric_model, variable_name, preview_value)
        self._formula: str = str(preview_value)
        self._dirty = False
        self.set_validator(FormulaChannelValidator(self.model, self))
        self.qt_widget.installEventFilter(self)
        self.qt_widget.textEdited.connect(self._on_user_edit)
        self.set_text(self._formula)
 
    def formula(self) -> str:
        return self._formula
 
    def setFormula(self, text: str) -> None:
        self.model.validate_formula(text)  # raises ValueError if unusable
        self._formula = text
        self._dirty = False
        self.set_text(text)
        self.formula_changed.emit(text)
 
    def evaluate_at(self, **variables) -> float:
        """Compute this formula for a real case, e.g.
        `field.evaluate_at(x=old_value)`. Raises ValueError for a result
        that's non-numeric, or numeric but outside this channel's
        mode/bounds/nan policy for this particular `x` - see the model
        docstrings (or the conversation this shipped from) for why a
        formula can be "valid" in the abstract yet still reject specific
        inputs. Use try_evaluate_at() on .model if you're sweeping many
        values and don't want one bad one to raise."""
        return self.model.evaluate_at(self._formula, **variables)
 
    def get_text(self):
        return self._formula
 
    def eventFilter(self, obj, event) -> bool:
        if obj is self.qt_widget:
            et = event.type()
            if et == QEvent.Type.FocusOut:
                self._commit()
            elif et == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self._commit()
                    self.select_all()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self._dirty = False
                    self.set_text(self._formula)  # discard edits, keep focus
                    self.select_all()
                    return True
        return super().eventFilter(obj, event)
 
    def _on_user_edit(self, _text: str) -> None:
        self._dirty = True
 
    def _commit(self) -> None:
        if not self._dirty:
            return
        text = self.get_true_text()
        try:
            self.model.validate_formula(text)
        except ValueError:
            self.set_text(self._formula)  # silently revert
        else:
            if text != self._formula:
                self._formula = text
                self.formula_changed.emit(self._formula)
        self._dirty = False
 
