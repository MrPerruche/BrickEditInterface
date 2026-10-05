from os import path, makedirs, listdir, remove
import re
import shutil
import tomllib, tomli_w
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime as _datetime, timezone as _tz, timedelta as _timedelta
from logging import getLogger

from send2trash import send2trash

from brickedit.src.brickedit.vhelper import net_ticks_now, to_net_ticks, from_net_ticks

from utils import dir_size

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface

_logger = getLogger(__name__)


class MetadataState(Enum):
    FOUND = auto()           # bei_metadata.toml was read
    MISSING = auto()         # No metadata file (Steam Cloud transfer, or backup made by an old BEI version)
    UNREADABLE = auto()      # Metadata file exists but is corrupt, too large or not a valid TOML
    NOT_APPLICABLE = auto()  # Brick Rigs backups, which never have BEI metadata


@dataclass(frozen=True)
class BackupInfo:
    path: str                # Backup folder, or .brv file (Brick Rigs backups and backups from older BEI versions)
    brv_path: str            # .brv file copied over Vehicle.brv when recovering this backup
    kind: str                # "st", "lt", "ug", "br_backup", "br_autosave" or "unknown"
    time: _datetime | None   # UTC, None if no trustworthy date was found
    description: str | None  # None if there is no description (see metadata for why)
    metadata: MetadataState

    @property
    def is_brick_rigs(self) -> bool:
        return self.kind in BackupSystem.BRICK_RIGS_BACKUP_FILES.values()

    @property
    def is_file(self) -> bool:
        return not path.isdir(self.path)


class BackupSystem:

    TOML_VERSION_TAG = "version"
    TOML_DESCRIPTION_TAG = "description"
    TOML_TIME_TAG = "time"

    BACKUP_SYSTEM_VERSION: int = 2
    SHORT_TERM_BACKUP_MAX_DAYS: int = 14
    BACKUPS_SUBDIR = ("brickedit-interface", "backups")
    METADATA_FILE = "bei_metadata.toml"

    # Backup names and metadata can be edited by the user: only trust dates within this range of years.
    MIN_BACKUP_YEAR = 2016
    MAX_BACKUP_YEAR = 2046
    # Larger metadata files are not read (a real one is ~100 bytes); longer descriptions are truncated.
    MAX_METADATA_SIZE = 64 * 1024
    MAX_DESCRIPTION_LENGTH = 1000

    # "<type>-<.NET ticks>", optionally followed by ".brv" (backups from older versions were plain files).
    # ASCII only: int() would also accept other unicode digits, underscores and whitespace.
    _BACKUP_NAME_RE = re.compile(r"([a-z]{2})-([0-9]{1,19})(\.brv)?", re.ASCII)
    BACKUP_TYPES = ("st", "lt", "ug")

    # Lowercase file name -> kind. Brick Rigs writes "Backup.brv" and "Autosave.brv" next to Vehicle.brv.
    BRICK_RIGS_BACKUP_FILES = {"backup.brv": "br_backup", "autosave.brv": "br_autosave"}

    # Fast undo deletes the backup it reverts to, so that undoing again goes one step further back
    FAST_UNDO_CONSUMES_BACKUP: bool = True
    # Fast undo asks for confirmation before reverting to a backup older than this. 0: always ask
    FAST_UNDO_CONFIRM_SETTING = "fast_undo_confirm_after_seconds"

    def __init__(self, mw: "BrickEditInterface"):
        self.main_window = mw
        self.not_eligible_for_lt = set()

        mw.settings.register("st_backup_count_limit", 6)
        mw.settings.register("st_backup_size_limit_kb", 8192)
        mw.settings.register("lt_backup_count_limit", 3)
        mw.settings.register("lt_backup_size_limit_kb", 8192)
        mw.settings.register(self.FAST_UNDO_CONFIRM_SETTING, 15 * 60)


    def full_backup_procedure(self, vehicle_path, description="No description provided."):
        if not (path.exists(vehicle_path) and path.isdir(vehicle_path)):
            return
        self.create_backup(vehicle_path, description)
        self.delete_excess(vehicle_path)


    def delete_excess(self, vehicle_path):
        for excess_dir_path in self.find_excess(vehicle_path):
            try:
                shutil.rmtree(excess_dir_path)
            except OSError:
                _logger.exception("Failed to delete excess backup %s", excess_dir_path)


    def create_backup(self, vehicle_path, description="No description provided.", user_generated = False):
        """Create a backup for a vehicle, given the path of the vehicle."""

        # Get relevant information
        time_now = net_ticks_now()
        og_brv = path.join(vehicle_path, "Vehicle.brv")
        if not path.exists(og_brv):
            print(f"BackupSystem::create_backup: Vehicle.brv not found i, {og_brv}.")
            return

        # Create the backup file structure
        # First backup of a creation per session is eligible for long_term status
        file_name = f"st-{time_now}"
        if user_generated:
            file_name = f"ug-{time_now}"
        elif vehicle_path not in self.not_eligible_for_lt:
            file_name = f"lt-{time_now}"
            self.not_eligible_for_lt.add(vehicle_path)
        backup_path = path.join(vehicle_path, *self.BACKUPS_SUBDIR, file_name)
        makedirs(backup_path, exist_ok=True)

        # Backup the BRV
        new_brv_path = path.join(backup_path, "Vehicle.brv")
        shutil.copy2(og_brv, new_brv_path)

        # Add a file containing BEI metadata.
        toml_file = path.join(backup_path, self.METADATA_FILE)
        with open(toml_file, "w") as f:
            toml_w = tomli_w.dumps({
                self.TOML_VERSION_TAG: self.BACKUP_SYSTEM_VERSION,
                self.TOML_DESCRIPTION_TAG: description,
                self.TOML_TIME_TAG: time_now
            })
            f.write(toml_w)


    def recover_backup(self, vehicle_path, backup: BackupInfo, backup_current: bool = True):
        """Overwrites Vehicle.brv with the backup's .brv. Unless backup_current is False (fast undo), the current
        Vehicle.brv is backed up first, like any other modification made by BEI.
        Raises OSError (FileNotFoundError if the backup has no .brv)."""
        if not path.isfile(backup.brv_path):
            raise FileNotFoundError(backup.brv_path)
        if backup_current:
            self.create_backup(vehicle_path, "Automatic backup made before recovering a backup.")
        shutil.copy2(backup.brv_path, path.join(vehicle_path, "Vehicle.brv"))
        # Only now: the recovered backup may itself have been excess
        if backup_current:
            self.delete_excess(vehicle_path)


    @staticmethod
    def delete_backup(backup_path: str, recycle_bin: bool):
        """Deletes a backup folder or file. Raises OSError on failure."""
        if recycle_bin:
            send2trash(backup_path)
        elif path.isdir(backup_path) and not BackupSystem._is_link(backup_path):
            shutil.rmtree(backup_path)
        else:
            remove(backup_path)


    # ---------------
    # Finding backups
    # ---------------

    @staticmethod
    def _is_link(p: str) -> bool:
        # Links could point anywhere: never treat them as backups (deleting their target would be bad)
        is_junction = getattr(path, "isjunction", None)  # Python 3.12+
        return path.islink(p) or (is_junction is not None and is_junction(p))


    def find_backup_names(self, vehicle_path):
        backups_root = path.join(vehicle_path, *self.BACKUPS_SUBDIR)
        if not path.isdir(backups_root):
            return []
        try:
            return listdir(backups_root)
        except OSError:
            return []

    def find_backups(self, vehicle_path):
        """Paths of every BEI backup of a vehicle (folders, or .brv files for backups from older versions)"""
        backups_root = path.join(vehicle_path, *self.BACKUPS_SUBDIR)
        result = []
        for name in self.find_backup_names(vehicle_path):
            backup_path = path.join(backups_root, name)
            if self._is_link(backup_path):
                continue
            if path.isdir(backup_path) or (path.isfile(backup_path) and name.lower().endswith(".brv")):
                result.append(backup_path)
        return result

    def find_brick_rigs_backups(self, vehicle_path) -> list[BackupInfo]:
        """Backup.brv and Autosave.brv, managed by Brick Rigs"""
        try:
            names = listdir(vehicle_path)
        except OSError:
            return []

        result = []
        for name in names:
            kind = self.BRICK_RIGS_BACKUP_FILES.get(name.lower())
            file_path = path.join(vehicle_path, name)
            if kind is None or self._is_link(file_path) or not path.isfile(file_path):
                continue
            try:
                time = _datetime.fromtimestamp(path.getmtime(file_path), tz=_tz.utc)
            except (OSError, OverflowError, ValueError):
                time = None
            result.append(BackupInfo(file_path, file_path, kind, time, None, MetadataState.NOT_APPLICABLE))
        return result


    # ---------------------
    # Reading backup info
    # ---------------------

    @classmethod
    def parse_backup_name(cls, name: str) -> tuple[str, int | None] | None:
        """(type, .NET ticks) from a backup's name, or None if it is not a valid backup name.
        Ticks are None if they don't represent a plausible date (see MIN/MAX_BACKUP_YEAR)."""
        match = cls._BACKUP_NAME_RE.fullmatch(name)
        if match is None or match.group(1) not in cls.BACKUP_TYPES:
            return None
        return match.group(1), cls.validate_ticks(int(match.group(2)))

    @classmethod
    def validate_ticks(cls, ticks) -> int | None:
        """ticks if it is an int representing a date between MIN_BACKUP_YEAR and MAX_BACKUP_YEAR, else None"""
        if type(ticks) is not int:  # Not isinstance: bool is an int
            return None
        try:
            year = from_net_ticks(ticks).year
        except (OverflowError, ValueError):
            return None
        return ticks if cls.MIN_BACKUP_YEAR <= year <= cls.MAX_BACKUP_YEAR else None


    def read_backup_metadata(self, backup_path) -> tuple[dict | None, MetadataState]:
        """Never raises: the metadata file may have been edited by hand, or be corrupt."""
        toml_file = path.join(backup_path, self.METADATA_FILE)
        try:
            if not path.isfile(toml_file) or self._is_link(toml_file):
                return None, MetadataState.MISSING
            if path.getsize(toml_file) > self.MAX_METADATA_SIZE:
                return None, MetadataState.UNREADABLE
            with open(toml_file, "rb") as f:
                return tomllib.load(f), MetadataState.FOUND
        except (OSError, ValueError, RecursionError):  # ValueError covers TOMLDecodeError and UnicodeDecodeError
            return None, MetadataState.UNREADABLE

    def fetch_backup_metadata(self, backup_path) -> dict:
        """Metadata of a backup, empty if it is missing or unreadable"""
        return self.read_backup_metadata(backup_path)[0] or {}


    def _get_backup_ticks(self, name_ticks: int | None, metadata: dict | None) -> int | None:
        """The backup's name is trusted first, the metadata second."""
        if name_ticks is not None:
            return name_ticks
        if metadata is None:
            return None
        return self.validate_ticks(metadata.get(self.TOML_TIME_TAG))


    def get_backup_info(self, backup_path) -> BackupInfo:
        name = path.basename(backup_path)
        parsed = self.parse_backup_name(name)
        kind, name_ticks = parsed if parsed is not None else ("unknown", None)

        if path.isdir(backup_path):
            brv_path = path.join(backup_path, "Vehicle.brv")
            metadata, metadata_state = self.read_backup_metadata(backup_path)
        else:  # Backup from an older version: the .brv itself, there never was any metadata
            brv_path = backup_path
            metadata, metadata_state = None, MetadataState.MISSING

        ticks = self._get_backup_ticks(name_ticks, metadata)
        time = from_net_ticks(ticks) if ticks is not None else None

        description = None
        if metadata is not None:
            description = metadata.get(self.TOML_DESCRIPTION_TAG)
            if not isinstance(description, str) or not description.strip():
                description = None
            elif len(description) > self.MAX_DESCRIPTION_LENGTH:
                description = description[:self.MAX_DESCRIPTION_LENGTH] + "…"

        return BackupInfo(backup_path, brv_path, kind, time, description, metadata_state)


    def get_all_backup_infos(self, vehicle_path) -> list[BackupInfo]:
        """Brick Rigs and BEI backups, newest first. Backups with an unknown date are last."""
        backups = self.find_brick_rigs_backups(vehicle_path) + [self.get_backup_info(p) for p in self.find_backups(vehicle_path)]
        backups.sort(key=lambda b: path.basename(b.path), reverse=True)  # Stable order among backups of equal date
        backups.sort(key=lambda b: (b.time is not None, b.time or _datetime.min.replace(tzinfo=_tz.utc)), reverse=True)
        return backups


    def find_latest_backup(self, vehicle_path) -> BackupInfo | None:
        """Newest recoverable BEI backup of a vehicle, used by fast undo. Backups with an unknown date are ignored:
        there is no telling whether they are the latest."""
        backups = [self.get_backup_info(p) for p in self.find_backups(vehicle_path)]
        recoverable = [b for b in backups if b.time is not None and path.isfile(b.brv_path)]
        # Ties are broken by name, like get_all_backup_infos
        return max(recoverable, key=lambda b: (b.time, path.basename(b.path)), default=None)


    def fast_undo_confirm_after(self) -> int | float:
        """Seconds, see FAST_UNDO_CONFIRM_SETTING. Settings can be edited by hand: invalid values (wrong type,
        negative, NaN) fall back to the default. inf is valid: never ask (but for backups dated in the future)."""
        value = self.main_window.settings.get(self.FAST_UNDO_CONFIRM_SETTING)
        if type(value) not in (int, float) or not value >= 0:  # Not isinstance: bool is an int. NaN fails >= 0
            return self.main_window.settings.get_default(self.FAST_UNDO_CONFIRM_SETTING)
        return value

    def fast_undo_needs_confirmation(self, backup: BackupInfo) -> bool:
        """Whether fast undo should ask before reverting to a (dated) backup: it is older than the delay set in the
        settings, or dated in the future (the clock or its name was changed: it may be much older than it looks)."""
        age = (_datetime.now(tz=_tz.utc) - backup.time).total_seconds()
        return not 0 <= age < self.fast_undo_confirm_after()


    # ---------------
    # Excess backups
    # ---------------

    def find_all_excess(self, vehicles_path):
        excess_backups = []
        if not vehicles_path or not path.isdir(vehicles_path):
            return excess_backups
        try:
            vehicle_pathes = listdir(vehicles_path)
        except OSError:
            return excess_backups
        for vehicle in vehicle_pathes:
            vehicle_path = path.join(vehicles_path, vehicle)
            if not path.isdir(vehicle_path):
                continue
            this_vehicle_excess = self.find_excess(vehicle_path)
            if this_vehicle_excess:
                excess_backups.extend(this_vehicle_excess)
        return excess_backups


    def find_excess(self, vehicle_path):
        # Get the timestamp of self.SHORT_TERM_BACKUP_MAX_DAYS ago in .NET ticks
        deletion_thresold = to_net_ticks(
            _datetime.now(tz=_tz.utc) - _timedelta(days=self.SHORT_TERM_BACKUP_MAX_DAYS)
        )
        excess_backups = []

        # Get the vehicle folder containing non-backup brv, brm, ...

        backups_root = path.join(vehicle_path, *self.BACKUPS_SUBDIR)
        if not path.isdir(backups_root):
            return []

        # Path & store upcoming results
        vehicle_backups = self.find_backup_names(vehicle_path)
        # backups: list[tuple[type, time, size, path]]
        found_backups: list[tuple[str, int, int, str]] = []

        # Sieve through backups
        for backup in vehicle_backups:
            # Get full backup path. Files (backups from older versions) are never deleted automatically.
            backup_path = path.join(backups_root, backup)
            if not path.isdir(backup_path) or self._is_link(backup_path):
                continue

            # Backups which aren't named properly, or whose date can't be trusted, are never deleted automatically
            parsed = self.parse_backup_name(backup)
            if parsed is None:
                continue
            backup_type, name_ticks = parsed
            metadata = None if name_ticks is not None else self.read_backup_metadata(backup_path)[0]
            backup_time = self._get_backup_ticks(name_ticks, metadata)
            if backup_time is None:
                continue

            try:
                backup_size = dir_size(backup_path)
            except OSError:
                continue

            # If a short term backup is too old, then it must be excess
            if backup_type == "st" and deletion_thresold > backup_time:
                excess_backups.append(backup_path)
                # Else add to list to be sorted youngest-oldest
            else:
                found_backups.append((backup_type, backup_time, backup_size, backup_path))

        # We now have the list of backups. Sort from newest to oldest, then prepare variables
        found_backups.sort(key=lambda x: x[1], reverse=True)
        count = {"st": 0, "lt": 0, "ug": 0}  # I'm too lazy to make if statements. Hey, if we ever add mid-term...
        size = {"st": 0, "lt": 0, "ug": 0}
        max_count = {
            "st": self.main_window.settings.get("st_backup_count_limit"),
            "lt": self.main_window.settings.get("lt_backup_count_limit"),
            "ug": 1e99
        }
        max_size = {
            "st": self.main_window.settings.get("st_backup_size_limit_kb") * 1024,
            "lt": self.main_window.settings.get("lt_backup_size_limit_kb") * 1024,
            "ug": 1e99
        }

        for backup_type, backup_time, backup_size, backup_path in found_backups:
            new_count = count[backup_type] + 1
            new_size = size[backup_type] + backup_size

            if new_count > max_count[backup_type] or new_size > max_size[backup_type]:
                excess_backups.append(backup_path)
            else:
                count[backup_type] = new_count
                size[backup_type] = new_size

        return excess_backups


    def get_backup_name(self, shorthand: str):
        match shorthand:
            case "st":
                return "Short term"
            case "lt":
                return "Long term"
            case "ug":
                return "User generated"
            case "br_backup":
                return "Brick Rigs"
            case "br_autosave":
                return "Brick Rigs autosave"
            case _:
                return "Unknown"
