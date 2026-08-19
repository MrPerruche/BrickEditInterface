from PySide6.QtGui import QRegularExpressionValidator, QValidator

HEX_4COLOR_VALIDATOR           = QRegularExpressionValidator(r"^[a-fA-F0-9]{8}$")
# BINARY_HEX_VALIDATOR           = QRegularExpressionValidator(r"^(?:[0-9A-Fa-f]{2}(?: ?[0-9A-Fa-f]{2})*)$")

ASCII_TEXT_ONLY                = QRegularExpressionValidator(r"^[ -~]*$")


# BINARY_HEX_VALIDATOR hates huge limits like 64KiB in regex


class HexBytesValidator(QValidator):
    def __init__(
        self,
        parent=None,
        *,
        min_bytes: int = 0,
        max_bytes: int | None = None,
    ):
        super().__init__(parent)

        if min_bytes < 0:
            raise ValueError("min_bytes cannot be negative")

        if max_bytes is not None and max_bytes < min_bytes:
            raise ValueError("max_bytes cannot be less than min_bytes")

        self.min_bytes = min_bytes
        self.max_bytes = max_bytes

    def validate(self, input: str, pos: int):
        if not input:
            return QValidator.State.Intermediate, input, pos

        # A trailing space means the user has completed the
        # previous byte and is starting the next one.
        trailing_space = input.endswith(" ")

        parts = input.split(" ")

        if trailing_space:
            parts.pop()

        # Empty components anywhere else mean consecutive spaces.
        if any(part == "" for part in parts):
            return QValidator.State.Invalid, input, pos

        # Validate each byte.
        for part in parts:
            if len(part) > 2:
                return QValidator.State.Invalid, input, pos

            if not all(c in "0123456789abcdefABCDEF" for c in part):
                return QValidator.State.Invalid, input, pos

        # Incomplete byte.
        if parts and len(parts[-1]) == 1:
            return QValidator.State.Intermediate, input, pos

        byte_count = len(parts)

        # Maximum number of bytes.
        if self.max_bytes is not None and byte_count > self.max_bytes:
            return QValidator.State.Invalid, input, pos

        # Can't start another byte once the maximum has been reached.
        if trailing_space:
            if self.max_bytes is not None and byte_count >= self.max_bytes:
                return QValidator.State.Invalid, input, pos

            return QValidator.State.Intermediate, input, pos

        # Minimum number of bytes.
        if byte_count < self.min_bytes:
            return QValidator.State.Intermediate, input, pos

        return QValidator.State.Acceptable, input, pos


BINARY_HEX_VALIDATOR_65535_MAX = HexBytesValidator(min_bytes=0, max_bytes=65535)
