from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Qt
from asteval import Interpreter
import math



class SafeMathLineEdit(QLineEdit):

    SYM_TABLE = {
        'pi': math.pi,
        'e': math.e,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'sqrt': math.sqrt,
        'log': math.log,
        'log10': math.log10,
        'log2': math.log2,
        'exp': math.exp,
        'abs': abs,
    }

    def __init__(self, value: float = 0.0, parent=None):
        super().__init__(parent)

        self._value: float = float(value)
        self.default_value: float = float(value)

        self.setAlignment(Qt.AlignLeft)
        self.setText(self._format(self._value))

        self.aeval = Interpreter()
        self.aeval.symtable.clear()
        self.aeval.symtable.update(self.SYM_TABLE)

        # Optional: expose current value as `x`
        self.aeval.symtable['x'] = self._value

        self.editingFinished.connect(self.evaluate_expression)
        self.returnPressed.connect(self.evaluate_expression)


    def _format(self, value: float) -> str:
        return str(round(value, 5))


    def evaluate_expression(self):
        expr = self.text().replace(',', '.')

        try:
            result = self.aeval(expr)

            if not isinstance(result, (int, float)):
                raise ValueError("Expression did not evaluate to a number")

            self._value = float(result)
            self.aeval.symtable['x'] = self._value
            self.setText(self._format(self._value))

        except Exception:
            # revert to last valid value
            self.setText(self._format(self._value))


    def value(self) -> float:
        self.evaluate_expression()
        return self._value

    def set_value(self, value: float):
        self._value = float(value)
        self.aeval.symtable['x'] = self._value
        self.setText(self._format(self._value))

    def reset(self):
        self.set_value(self.default_value)
