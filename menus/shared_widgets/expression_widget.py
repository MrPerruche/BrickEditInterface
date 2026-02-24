import math
import numpy as np
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable

from asteval import Interpreter

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QMessageBox
from PySide6.QtCore import Signal


class ExpressionType(Enum):

    INTEGER = auto()
    FLOAT = auto()
    DOUBLE = auto()
    MATH_EXPR = auto()
    PYTHON_EXPR = auto()

    def is_py_float(self) -> bool:
        return self in (ExpressionType.FLOAT, ExpressionType.DOUBLE)

    def must_calc_immediately(self) -> bool:
        return self not in (ExpressionType.MATH_EXPR, ExpressionType.PYTHON_EXPR)


@dataclass(frozen=True)
class ExpressionSymbol:
    sym: str
    value_getter: Callable[[], Any]
    user_desc: str | None


def safe_fact(n):
    if n > 1000:
        return math.nan
    return math.factorial(n)


DEFAULT_SYMBOLS: list[ExpressionSymbol] = [
    # Roots
    ExpressionSymbol("sqrt", lambda: math.sqrt, None),
    ExpressionSymbol("cbrt", lambda: math.cbrt, None),
    # Logarithms
    ExpressionSymbol("log", lambda: math.log, None),
    ExpressionSymbol("log2", lambda: math.log2, None),
    ExpressionSymbol("log10", lambda: math.log10, None),
    # Other
    ExpressionSymbol("fact", lambda: math.factorial, None),
    ExpressionSymbol("exp", lambda: math.exp, None),
    # Trigonometry
    ExpressionSymbol("sin", lambda: math.sin, None),
    ExpressionSymbol("cos", lambda: math.cos, None),
    ExpressionSymbol("tan", lambda: math.tan, None),
    ExpressionSymbol("asin", lambda: math.asin, None),
    ExpressionSymbol("asinh", lambda: math.asinh, None),
    ExpressionSymbol("acos", lambda: math.acos, None),
    ExpressionSymbol("acosh", lambda: math.acosh, None),
    ExpressionSymbol("atan", lambda: math.atan, None),
    ExpressionSymbol("atan2", lambda: math.atan2, None),
    ExpressionSymbol("atanh", lambda: math.atanh, None),
    # Numbers
    ExpressionSymbol("inf", lambda: math.inf, None),
    ExpressionSymbol("nan", lambda: math.nan, None),
    ExpressionSymbol("e", lambda: math.e, None),
    ExpressionSymbol("pi", lambda: math.pi, None),
    # Rounding
    ExpressionSymbol("abs", lambda: abs, None),
    ExpressionSymbol("ceil", lambda: math.ceil, None),
    ExpressionSymbol("round", lambda: round, None),
    ExpressionSymbol("floor", lambda: math.floor, None),
    ExpressionSymbol("sign", lambda: lambda x: (1 if x > 0 else -1 if x < 0 else 0), None),
    ExpressionSymbol("nextafter", lambda: math.nextafter, None),
]

REPLACEMENT_TABLE: list[tuple[str, str]] = [
    # (',', '.'),
    ('^', '**'),
    ('_XOR', '^')
]


class ExpressionWidget(QWidget):

    editingFinished = Signal(str)

    def __init__(self,
        default: str,
        expression_type: ExpressionType,
        clamps: tuple[float | None, float | None] = (None, None),
        custom_sym: list[ExpressionSymbol] | None = None,
        custom_restriction: Callable[[str], bool] | None = None,
        must_warn_user: bool = True,
        display_round_digits: int = 3,

        parent = None
    ):
        """
        Args:
            default (str): Default value
            expression_type (ExpressionType): Type of the expression widget, restricts the niputs
            clamps (tuple[float|None, float|None]): Bounds numerical values
            custom_sym (list[ExpressionSymbol]): list of custom symbols available to the user during evaluation
            custom_restriction (Callable[[str], bool]): Callable telling if an input is acceptable in this context or not
            must_warn_user (bool): Send a pyside6 messagebox if the evaluation fails
        """
        super().__init__(parent)

        # Store basic data
        self.expression_type = expression_type
        self.default: str = str(default)
        self.full_value: float | int | None = None
        if self.expression_type.is_py_float():
            try:
                self.full_value = float(self.default)
            except ValueError:
                self.full_value = None

        self.clamps = clamps
        self.custom_restriction = custom_restriction
        self.must_warn_user = must_warn_user
        self.display_round_digits = display_round_digits

        # Build symbols list. Order of sym matters
        self.sym: list[ExpressionSymbol] = []
        try:  # Add default as x if x isn't defined and its possible
            default_f = float(self.default)
            has_custom_x = False
            if custom_sym is not None:
                for csym in custom_sym:
                    if csym.sym == 'x':
                        has_custom_x = True
            if not has_custom_x:
                self.sym.append(ExpressionSymbol('x', lambda: default_f, None))
        except ValueError:
            self.sym.append(ExpressionSymbol('x', lambda: 1, None))

        if custom_sym is not None:
            self.sym.extend(custom_sym)
        self.sym.extend(DEFAULT_SYMBOLS)

        self.interpreter = Interpreter(
            minimal=True,
            builtins_readonly=True,
            no_import=True,
        )


        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.setSpacing(0)
        self.setLayout(self.master_layout)

        self.line_edit = QLineEdit()
        self.line_edit.setText(self.default)
        self.line_edit.setPlaceholderText(self.default)
        self.line_edit.editingFinished.connect(self.validate_new_input)
        self.line_edit.focusInEvent = self._focus_in_event
        self.last_valid_line_edit_text = self.default
        if self.expression_type.is_py_float() and self.full_value is not None:
            self._display_rounded()

        self.master_layout.addWidget(self.line_edit)


    # FOCUS METHODS FOR THE LINE EDIT
    def _focus_in_event(self, event):
        QLineEdit.focusInEvent(self.line_edit, event)
        self._display_full_precision()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self.expression_type.is_py_float() and self.full_value is not None:
            self._display_rounded()


    # DISPLAY METHODS FOR FOCUS IN / OUT
    def _ulp(self, value: float) -> float:
        if self.expression_type == ExpressionType.FLOAT:
            v32 = np.float32(value)
            return float(np.spacing(v32))
        else:
            return math.ulp(value)
    
    
    def _display_full_precision(self):
        if not self.expression_type.is_py_float():
            return

        if self.full_value is None:
            return

        if self.expression_type == ExpressionType.FLOAT:
            value = float(np.float32(self.full_value))
            text = f"{value:.8g}"
        else:
            text = str(self.full_value)

        # Only update if different
        if self._get_raw_text() != text:
            self.line_edit.setText(text)


    def _format_float_for_display(self, value: float) -> str:
        digits = self.display_round_digits

        # Convert to medium precision first
        if self.expression_type == ExpressionType.FLOAT:
            medium_value = float(np.float32(value))
        else:
            medium_value = value

        rounded = round(medium_value, digits)

        # Compute tolerance based on representable precision
        tol = 2 * self._ulp(medium_value)

        # If difference is within floating representation error, treat as exact
        text = f"{rounded:.{digits}f}"
        if abs(medium_value - rounded) <= tol:
            text = text.rstrip('0').rstrip('.')

        return text

    def _display_rounded(self):
        if self.expression_type.is_py_float() and self.full_value is not None:
            self.line_edit.setText(
                self._format_float_for_display(self.full_value)
            )


    # GETTERS
    def _get_raw_text(self):
        return self.line_edit.text()


    def get_text(self):
        if self.expression_type == ExpressionType.FLOAT:
            return f"{self.full_value}"
        #else:
        return self._get_raw_text()


    def get_value_str(self) -> str:
        text = self._get_raw_text()
        if text == '':
            text = self.default
        for old_expr, new_expr in REPLACEMENT_TABLE:
            text = text.replace(old_expr, new_expr)
        return text


    def value(self, extra_sym: list[ExpressionSymbol] = None) -> int | float:

        # Evaluated at runtime ?
        if not self.expression_type.must_calc_immediately():

            value = self.evaluate(force=True, extra_sym=[] if extra_sym is None else extra_sym)
            if not self.expression_type == ExpressionType.PYTHON_EXPR:
                value = float(value)

        elif self.expression_type.is_py_float():
            value = float(self.full_value)

        else:  # self.expression_type == ExpressionType.INTEGER
            value = int(self.get_value_str())

        return value


    def setText(self, text: str):
        self.line_edit.setText(text)
        self.last_valid_line_edit_text = text


    def validate_new_input(self):
        # Try to evaluate. Will return None if the input is invalid,
        # or the current contents if it should not be modified

        e = None  # We run code at the end if result is None OR there is an error

        try:
            result = self.evaluate()
            if result is not None:

                if self.expression_type.is_py_float():
                    numeric = float(result)
                    self.full_value = numeric

                    self._display_rounded()

                    self.last_valid_line_edit_text = self._get_raw_text()
                    self.editingFinished.emit(str(numeric))

                else:
                    self.line_edit.setText(result)
                    self.last_valid_line_edit_text = result
                    self.editingFinished.emit(result)

                return

            # Return to not trigger the fail logic

        except BaseException as ex:
            e = ex

        # If evaluating failed / there was an error, undo changes
        self.line_edit.setText(self.last_valid_line_edit_text)
        if e is not None:
            QMessageBox.warning(None,
                "Invalid expression",
                f"The given expression could not be treated: {str(e)}"
            )


    def evaluate(self, *args, force: bool = False, extra_sym: list[ExpressionSymbol] | None = None) -> str | None:
        """Force will evaluate even if it's an expression"""

        if extra_sym is None:
            extra_sym = []

        self.interpreter.symtable.clear()
        self.interpreter.symtable.update({sym.sym: sym.value_getter() for sym in self.sym})
        self.interpreter.symtable.update({sym.sym: sym.value_getter() for sym in extra_sym})
        # print(self.interpreter.symtable)
        self.interpreter.error = []  # Clear the traceback

        try:
            # Percent support
            final_mult = 1
            value_str = self.get_value_str()
            if value_str.endswith('%'):
                value_str = value_str[:-1]
                final_mult /= 100
            
            output = self.interpreter(value_str)
            num_result = -1

            if self.interpreter.error:  # Traceback is not empty? Raise
                e = self.interpreter.error[-1]
                raise RuntimeError(
                    f"An error occured while parsing the expression:\n{e.msg}"
                )

            if not isinstance(output, (float, int)):
                raise ValueError("This input does not evaluate to a numerical value.")

            # If we do not calc immediately, interpreter is only good to check for errors
            if not self.expression_type.must_calc_immediately() and not force:
                return self.get_value_str()
            # Cast to right type as str
            elif self.expression_type is ExpressionType.INTEGER:
                num_result = int(float(output))
            else:
                num_result = float(output)

            assert num_result is not None, "Num result is None?"
            num_result *= final_mult  # Percent support

            # Apply clamps
            mn, mx = self.clamps
            if mn is not None and num_result < mn:
                num_result = mn
            if mx is not None and num_result > mx:
                num_result = mx

            return str(num_result)


        except BaseException as e:
            if self.must_warn_user:
                QMessageBox.warning(None,
                    "Invalid expression",
                    f"The given expression could not evaluated: {str(e)}\n\nNote: you are not allowed to use commas for decimals. Use dots to mark the decimal places"
                )

        # If we are here something went wrong
        return None
