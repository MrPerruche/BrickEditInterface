import ast
import math
import warnings

from PySide6.QtGui import QValidator

from asteval import Interpreter

from ui.widgets.number_channel import _UNSAFE_SYMBOLS, _check_single_expression, _friendly_error, _safe_factorial
from ui.models import TooltipContents

import brickedit

from typing import TYPE_CHECKING, Callable
if TYPE_CHECKING:
    from ui.components.vehicle.vehicle_data import VehicleData


CONDITION_VARIABLES_TOOLTIP = TooltipContents(
    "Condition variables",
    "<code>x</code>, <code>y</code>, <code>z</code>: position (cm)\n"
    "<code>rx</code>, <code>ry</code>, <code>rz</code>: rotation (degrees)\n"
    "<code>sx</code>, <code>sy</code>, <code>sz</code>: brick size (cm, 0 if the brick has no size)\n"
    "<code>r</code>, <code>g</code>, <code>b</code>, <code>a</code>: color (0-255, 0 if the brick has no color)\n"
    "<code>type</code>: internal brick type, eg. <code>type == 'ScalableBrick'</code>\n"
    "<code>i</code>: index of the brick in the vehicle, <code>n</code>: number of bricks\n"
    "<code>editor</code>, <code>weld</code>: name of the brick's named group, or <code>''</code>\n"
    "<code>prop('BrickMaterial')</code>: value of any property (<code>None</code> if the brick doesn't have it)\n"
    "<code>has('BrickSize')</code>: whether the brick has a property\n\n"
    "Example: <code>y &gt; 0 and sz &lt;= 10 and type == 'ScalableBrick'</code>"
)


def _get_property(brick: brickedit.Brick, name: str):
    try:
        return brick.get_property(name)
    except brickedit.BrickError:
        return None

def _size(brick: brickedit.Brick, axis: int) -> float:
    size = _get_property(brick, brickedit.p.BRICK_SIZE)
    return size.as_tuple()[axis] if isinstance(size, brickedit.Vec3) else 0.0

def _color(brick: brickedit.Brick, shift: int) -> int:
    color = _get_property(brick, brickedit.p.BRICK_COLOR)
    return color >> shift & 0xFF if isinstance(color, int) else 0

def _index(brick: brickedit.Brick, data: 'VehicleData | None') -> int:
    return data.brick_indices.get(brick.ref.id, -1) if data is not None else 0

def _group(brick: brickedit.Brick, data: 'VehicleData | None', editor: bool) -> str:
    if data is None:
        return ""
    return (data.editor_be_to_bei.get(brick.ref.editor, "") if editor
            else data.weld_be_to_bei.get(brick.ref.weld, ""))


# Variable name -> value for a brick. See CONDITION_VARIABLES_TOOLTIP
VARIABLES: dict[str, Callable[[brickedit.Brick, 'VehicleData | None'], object]] = {
    'x': lambda b, d: b.pos.x, 'y': lambda b, d: b.pos.y, 'z': lambda b, d: b.pos.z,
    'rx': lambda b, d: b.rot.x, 'ry': lambda b, d: b.rot.y, 'rz': lambda b, d: b.rot.z,
    'sx': lambda b, d: _size(b, 0), 'sy': lambda b, d: _size(b, 1), 'sz': lambda b, d: _size(b, 2),
    'r': lambda b, d: _color(b, 24), 'g': lambda b, d: _color(b, 16), 'b': lambda b, d: _color(b, 8),
    'a': lambda b, d: _color(b, 0),
    'type': lambda b, d: b.meta().name(),
    'i': _index,
    'n': lambda b, d: len(d.brvfile.bricks) if d is not None else 1,
    'editor': lambda b, d: _group(b, d, True),
    'weld': lambda b, d: _group(b, d, False),
}


SAMPLE_BRICK = brickedit.Brick(brickedit.ID("sample"), brickedit.bt.SCALABLE_BRICK)


class ConditionModel:
    """One condition. parse() it, then evaluate() it on as many bricks as needed."""

    def __init__(self):
        self._aeval = Interpreter(minimal=True, with_ifexp=True)
        symtable = self._aeval.symtable
        for name in _UNSAFE_SYMBOLS:
            symtable.pop(name, None)
        symtable.update(pi=math.pi, e=math.e, inf=math.inf, nan=math.nan, factorial=_safe_factorial)

        # prop() and has() read the brick being evaluated: bound once rather than once per brick
        self._brick: brickedit.Brick = SAMPLE_BRICK
        symtable['prop'] = lambda name: _get_property(self._brick, name)
        symtable['has'] = lambda name: name in self._brick.ppatch or name in self._brick.meta().p

        self._node = None
        self._getters: list[tuple[str, Callable]] = []  # Variables used by the condition
        self.text = ""

    def is_parsed(self) -> bool:
        return self._node is not None

    def parse(self, text: str):
        """Raises ValueError (with a message for the user) if text isn't a single valid expression."""
        text = text.strip()
        if not text:
            raise ValueError("empty condition")
        _check_single_expression(text)
        try:
            node = self._aeval.parse(text)
        except SyntaxError as e:
            raise ValueError(f"Invalid syntax: {e}") from None
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        self._getters = [(name, getter) for name, getter in VARIABLES.items() if name in names]
        self._node = node
        self.text = text

    def clear(self):
        self._node = None
        self._getters = []
        self.text = ""

    def evaluate(self, brick: brickedit.Brick, vehicle_data: 'VehicleData | None') -> bool:
        """Raises ValueError if the condition fails for this brick (eg. prop('Missing').x)."""
        if self._node is None:
            raise ValueError("no condition")
        self._brick = brick
        symtable = self._aeval.symtable
        for name, getter in self._getters:
            symtable[name] = getter(brick, vehicle_data)
        self._aeval.error = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = self._aeval.run(self._node, with_raise=False)
        if self._aeval.error:
            name, msg = self._aeval.error[0].get_error()
            raise ValueError(_friendly_error(name, msg))
        try:
            return bool(result)
        except (TypeError, ValueError):  # eg. numpy arrays
            raise ValueError("the condition must be true or false") from None


class ConditionValidator(QValidator):
    """Acceptable if the condition parses and only uses known names (checked on a sample brick). Errors which
    depend on the brick (eg. prop('BrickSize').z on a brick without size) are only found when filtering."""

    def __init__(self, sample: Callable[[], tuple[brickedit.Brick, 'VehicleData | None']], parent=None):
        super().__init__(parent)
        self.sample = sample
        self._model = ConditionModel()
        self.last_error: str | None = None

    def validate(self, text: str, pos: int):
        self.last_error = None
        if not text.strip():
            return QValidator.State.Intermediate, text, pos
        try:
            self._model.parse(text)
            self._model.evaluate(*self.sample())
        except ValueError as e:
            message = str(e)
            if message.startswith(("Invalid syntax", "Unknown name", "empty")):
                self.last_error = message
                return QValidator.State.Intermediate, text, pos
        return QValidator.State.Acceptable, text, pos
