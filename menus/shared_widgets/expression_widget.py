import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable

from asteval import Interpreter

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QMessageBox
from PySide6.QtCore import Signal


class ExpressionType(Enum):

    INTEGER = auto()
    FLOAT = auto()
    MATH_EXPR = auto()
    PYTHON_EXPR = auto()

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
        self.default = str(default)
        self.expression_type = expression_type
        self.clamps = clamps
        self.custom_restriction = custom_restriction
        self.must_warn_user = must_warn_user

        # Build symbols list. Order of sym matters
        self.sym = [ExpressionSymbol('x', lambda: float(self.default), None)]
        if custom_sym is not None:
            self.sym.extend(custom_sym)
        self.sym.extend(DEFAULT_SYMBOLS)

        self.interpreter = Interpreter(
            minimal=True,
            builtins_readonly=True,
            no_import=True,
            # readonly_symbols=True,
        )


        self.master_layout = QVBoxLayout()
        self.master_layout.setContentsMargins(0, 0, 0, 0)
        self.master_layout.setSpacing(0)
        self.setLayout(self.master_layout)

        self.line_edit = QLineEdit()
        self.line_edit.setText(self.default)
        self.line_edit.setPlaceholderText(self.default)
        self.line_edit.editingFinished.connect(self.validate_new_input)
        self.last_valid_line_edit_text = self.default

        self.master_layout.addWidget(self.line_edit)


    def get_text(self):
        return self.line_edit.text()


    def get_value_str(self) -> str:
        text = self.get_text()
        if text == '':
            text = self.default
        for old_expr, new_expr in REPLACEMENT_TABLE:
            text = text.replace(old_expr, new_expr)
        return text


    def value(self) -> int | float:
        # Evaluated at runtime ?
        if not self.expression_type.must_calc_immediately():
            value = float(self.evaluate(force=True))
        else:
            value = self.get_value_str()
            if self.expression_type == ExpressionType.INTEGER:
                value = int(value)
            elif self.expression_type == ExpressionType.FLOAT:
                value = float(value)
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
                # Update contents because it may be calculated or reformatted
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


    def evaluate(self, *args, force: bool = False) -> str | None:
        """Force will evaluate even if it's an expression"""


        self.interpreter.symtable.clear()
        self.interpreter.symtable.update({sym.sym: sym.value_getter() for sym in self.sym})
        # print(self.interpreter.symtable)
        self.interpreter.error = []  # Clear the traceback

        try:
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
            num_result *= final_mult

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
