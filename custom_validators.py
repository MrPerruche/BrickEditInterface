import re
from PySide6.QtGui import QValidator


_FLOAT_RE = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"


class TupleFloatValidator(QValidator):
    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self.count = count

        values = r"\s*,\s*".join([f"({_FLOAT_RE})"] * count)

        # Final regex: allow "(a, b)" OR "a, b"
        self._final_re = re.compile(
            rf"^(?:\(\s*{values}\s*\)|{values})$"
        )

    def validate(self, text: str, pos: int):
        text = text.strip()

        # Empty or early typing
        if not text:
            return QValidator.Intermediate, text, pos

        # Accept valid final form
        if self._final_re.match(text):
            return QValidator.Acceptable, text, pos

        # ----- Intermediate typing rules -----

        # Allow optional opening parenthesis
        if text == "(":
            return QValidator.Intermediate, text, pos

        # Strip leading "(" for intermediate checks
        working = text[1:] if text.startswith("(") else text

        # Too many commas → invalid
        if working.count(",") >= self.count:
            return QValidator.Invalid, text, pos

        # Allow partial float entries
        tokens = working.split(",")

        for token in tokens:
            token = token.strip()
            if token and not re.match(rf"^{_FLOAT_RE}$", token):
                return QValidator.Intermediate, text, pos

        return QValidator.Intermediate, text, pos



class AsciiOnlyValidator(QValidator):
    def validate(self, text: str, pos: int):
        # All characters must be ASCII (0–127)
        if all(ord(c) < 128 for c in text):
            return QValidator.Acceptable, text, pos

        return QValidator.Invalid, text, pos
