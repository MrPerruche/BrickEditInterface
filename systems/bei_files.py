"""BEI's shareable files: rule presets (.beirules) for now, other kinds later (eg. brick extensions, .beiext).

Every kind is a TOML document with the same header, so all of them are read, checked and stored the same way:

    [bei]
    kind = "rule_preset"     # What the file holds
    version = 1              # Version of this kind's format. Older versions are read, newer ones refused
    app_version = "2.0.0"    # Version of BEI which wrote the file (informative)

    [content]                # The data itself, defined by the kind
    ...

Files are user data, possibly made by someone else: everything read from them is checked (ConfigReader helps),
and a broken file never prevents loading the others (FileLibrary.load_all). Nothing in them is ever executed:
formulas are stored as text and evaluated with asteval, like everywhere else.
"""

import re
import shutil
import tomllib
import tomli_w
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Generic, TypeVar, Any

from platformdirs import user_config_dir

import var
from systems.settings import SettingsManagerV2

import brickedit

from logging import getLogger
_logger = getLogger(__name__)


T = TypeVar("T")
E = TypeVar("E", bound=Enum)

MAX_FILE_SIZE = 4 * 1024 * 1024  # Bigger files are refused without being parsed
MAX_STEM_LENGTH = 80
_FORBIDDEN_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_STEMS = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)), *(f"lpt{i}" for i in range(10))}


class BeiFileError(Exception):
    """A file can't be read, written or understood. The message is meant to be shown to the user as is."""


# ---------- Reading content safely


class ConfigReader:
    """Typed access to a table read from a file. Missing keys give the default (files from older versions may
    lack them); values of the wrong type raise BeiFileError (the file is broken or was tampered with)."""

    def __init__(self, data: Any, where: str):
        if not isinstance(data, dict):
            raise BeiFileError(f"{where} must be a table.")
        self.data = data
        self.where = where

    def _get(self, key: str, default, check: Callable[[Any], bool], expected: str):
        if key not in self.data:
            return default
        value = self.data[key]
        if not check(value):
            raise BeiFileError(f"{self.where}: \"{key}\" must be {expected}.")
        return value

    def get_str(self, key: str, default: str = "") -> str:
        return self._get(key, default, lambda v: isinstance(v, str), "text")

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self._get(key, default, lambda v: isinstance(v, bool), "true or false")

    def get_int(self, key: str, default: int = 0, minimum: int | None = None, maximum: int | None = None) -> int:
        value = self._get(key, default, lambda v: isinstance(v, int) and not isinstance(v, bool), "an integer")
        if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
            raise BeiFileError(f"{self.where}: \"{key}\" must be between {minimum} and {maximum}.")
        return value

    def get_float(self, key: str, default: float = 0.0, minimum: float | None = None,
                  maximum: float | None = None) -> float:
        value = float(self._get(key, default, _is_number, "a number"))
        if value != value or value in (float("inf"), float("-inf")) or (minimum is not None and value < minimum) or (
                maximum is not None and value > maximum):
            if minimum is not None and maximum is not None:
                limits = f" between {minimum} and {maximum}"
            elif minimum is not None:
                limits = f" of at least {minimum}"
            else:
                limits = f" of at most {maximum}" if maximum is not None else ""
            raise BeiFileError(f"{self.where}: \"{key}\" must be a finite number{limits}.")
        return value

    def get_vec3(self, key: str, default: brickedit.Vec3) -> brickedit.Vec3:
        value = self._get(key, None, lambda v: isinstance(v, list) and len(v) == 3 and all(map(_is_number, v)),
                          "a list of 3 numbers")
        return default if value is None else brickedit.Vec3(*(float(c) for c in value))

    def get_choice(self, key: str, choices: tuple[str, ...], default: str) -> str:
        return self._get(key, default, lambda v: v in choices, "one of " + ", ".join(f'"{c}"' for c in choices))

    def get_enum(self, key: str, enum_cls: type[E], default: E) -> E:
        """Enum stored by its member's name, in lower case (eg. FilterMode.MUST_NOT is "must_not")"""
        names = tuple(member.name.lower() for member in enum_cls)
        return enum_cls[self.get_choice(key, names, default.name.lower()).upper()]

    def get_tables(self, key: str) -> list['ConfigReader']:
        tables = self._get(key, [], lambda v: isinstance(v, list), "a list of tables")
        return [ConfigReader(table, f"{self.where}, {key} #{i + 1}") for i, table in enumerate(tables)]

    def get_raw(self, key: str, default=None):
        return self.data.get(key, default)


def _is_number(value) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def enum_key(member: Enum) -> str:
    """How ConfigReader.get_enum expects an enum member to be stored"""
    return member.name.lower()


# ---------- File format


@dataclass(frozen=True)
class BeiFileFormat:
    kind: str          # Written in the header, checked when reading
    extension: str     # Eg. ".beirules"
    version: int       # Version written. Readers get the file's version, to upgrade older content
    description: str   # Eg. "rule preset". Used in messages and file dialogs

    def name_filter(self) -> str:
        """For QFileDialog"""
        return f"BEI {self.description}s (*{self.extension})"

    def dumps(self, content: dict) -> str:
        return tomli_w.dumps({
            "bei": {"kind": self.kind, "version": self.version, "app_version": var.VERSION_FULL},
            "content": content,
        })

    def loads(self, text: str) -> tuple[dict, int]:
        """Returns (content, version of the file). Raises BeiFileError."""
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            raise BeiFileError(f"This is not a valid {self.description} file: {e}.") from e

        header = data.get("bei")
        if not isinstance(header, dict) or "kind" not in header:
            raise BeiFileError(f"This is not a {self.description} file: it has no [bei] header.")
        if header["kind"] != self.kind:
            raise BeiFileError(f"This file holds a \"{header['kind']}\", not a {self.description}.")
        version = header.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise BeiFileError(f"This {self.description} file has an invalid version.")
        if version > self.version:
            raise BeiFileError(f"This {self.description} was made with a newer version of BrickEdit-Interface. "
                               "Update BrickEdit-Interface to use it.")
        content = data.get("content")
        if not isinstance(content, dict):
            raise BeiFileError(f"This {self.description} file has no content.")
        return content, version

    def read(self, path: Path) -> tuple[dict, int]:
        """Returns (content, version of the file). Raises BeiFileError."""
        try:
            if path.stat().st_size > MAX_FILE_SIZE:
                raise BeiFileError(f"{path.name} is too big to be a {self.description}.")
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            raise BeiFileError(f"{path.name} could not be read: {e}") from e
        return self.loads(text)

    def write(self, path: Path, content: dict):
        """Raises BeiFileError. The file is replaced at once: a failed write never leaves half a file."""
        text = self.dumps(content)
        temp = path.with_name(path.name + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp.write_text(text, encoding="utf-8")
            temp.replace(path)
        except OSError as e:
            temp.unlink(missing_ok=True)
            raise BeiFileError(f"{path.name} could not be saved: {e}") from e


def safe_file_stem(name: str, fallback: str) -> str:
    """A file name (without extension) made from a name typed by the user, valid on every OS"""
    stem = _FORBIDDEN_CHARS.sub("_", name).strip().rstrip(".")[:MAX_STEM_LENGTH].strip()
    if not stem or stem.lower() in _RESERVED_STEMS:
        return fallback
    return stem


# ---------- Library


@dataclass
class LibraryEntry(Generic[T]):
    path: Path
    item: T | None = None      # None if the file couldn't be loaded
    error: str | None = None   # Why, for the user


class FileLibrary(Generic[T]):
    """The user's files of one format, in a folder of BEI's config directory (next to settings.toml).

    decode turns the content of a file into an item, and raises BeiFileError (or ValueError / KeyError /
    TypeError) if the content is invalid."""

    def __init__(self, file_format: BeiFileFormat, folder_name: str, decode: Callable[[dict, int, Path], T]):
        self.format = file_format
        self.folder = Path(user_config_dir(SettingsManagerV2.APP_NAME)) / folder_name
        self.decode = decode

    def files(self) -> list[Path]:
        try:
            return sorted((p for p in self.folder.glob(f"*{self.format.extension}") if p.is_file()),
                          key=lambda p: p.name.lower())
        except OSError:
            _logger.exception(f"Could not list {self.folder}")
            return []

    def load(self, path: Path) -> T:
        """Reads and decodes one file. Raises BeiFileError, whatever went wrong."""
        content, version = self.format.read(path)
        try:
            return self.decode(content, version, path)
        except BeiFileError:
            raise
        except (ValueError, KeyError, TypeError) as e:
            raise BeiFileError(f"This {self.format.description} is invalid: {e}") from e

    def load_all(self) -> list[LibraryEntry[T]]:
        """Every file of the folder. Files which fail to load are returned with their error."""
        entries = []
        for path in self.files():
            try:
                entries.append(LibraryEntry(path, item=self.load(path)))
            except BeiFileError as e:
                _logger.warning(f"Could not load {path}: {e}")
                entries.append(LibraryEntry(path, error=str(e)))
            except Exception as e:  # Never let one file break the menu
                _logger.exception(f"Unexpected error while loading {path}")
                entries.append(LibraryEntry(path, error=f"Unexpected error: {e}"))
        return entries

    def free_path(self, name: str, fallback: str) -> Path:
        """Path for a new file named after name, which doesn't exist yet"""
        stem = safe_file_stem(name, fallback)
        path = self.folder / f"{stem}{self.format.extension}"
        n = 2
        while path.exists():
            path = self.folder / f"{stem} ({n}){self.format.extension}"
            n += 1
        return path

    def save(self, path: Path, content: dict):
        """Creates or replaces path, which must be in the library's folder. Raises BeiFileError."""
        self.format.write(path, content)

    def import_file(self, source: Path, name: str, fallback: str, replace: Path | None = None) -> Path:
        """Copies a file (already loaded successfully) into the library, as a new file named after name, or over
        replace. Raises BeiFileError."""
        destination = replace if replace is not None else self.free_path(name, fallback)
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            if source.resolve() != destination.resolve():
                shutil.copyfile(source, destination)
        except OSError as e:
            raise BeiFileError(f"{source.name} could not be imported: {e}") from e
        return destination

    def export_file(self, path: Path, destination: Path):
        """Raises BeiFileError."""
        try:
            if path.resolve() != destination.resolve():
                shutil.copyfile(path, destination)
        except OSError as e:
            raise BeiFileError(f"{path.name} could not be exported: {e}") from e

    def delete(self, path: Path):
        """Raises BeiFileError."""
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            raise BeiFileError(f"{path.name} could not be deleted: {e}") from e
