import os
import shutil
import tomllib, tomli_w
from datetime import datetime as _datetime, timezone as _tz, timedelta as _timedelta

from brickedit.src.brickedit.vhelper import net_ticks_now, to_net_ticks

from utils import dir_size

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mainwindow import BrickEditInterface


class BackupSystem:

    BACKUP_SYSTEM_VERSION: int = 2
    SHORT_TERM_BACKUP_MAX_DAYS: int = 14
    BACKUPS_SUBDIR = ("brickedit-interface", "backups")

    def __init__(self, mw: "BrickEditInterface"):
        self.main_window = mw
        self.not_eligible_for_lt = set()


    def full_backup_procedure(self, vehicle_path, description="No description provided."):
        self.create_backup(vehicle_path, description)
        excess = self.find_excess(vehicle_path)
        for excess_dir_path in excess:
            shutil.rmtree(excess_dir_path)


    def create_backup(self, vehicle_path, description="No description provided."):
        """Create a backup for a vehicle, given the path of the vehicle."""

        # Get relevant information
        time_now = net_ticks_now()
        og_brv = os.path.join(vehicle_path, "Vehicle.brv")
        if not os.path.exists(og_brv):
            print(f"BackupSystem::create_backup: Vehicle.brv not found i, {og_brv}.")
            return

        # Create the backup file structure
        # First backup of a creation per session is eligible for long_term status
        file_name = f"st-{time_now}"
        if vehicle_path not in self.not_eligible_for_lt:
            file_name = f"lt-{time_now}"
            self.not_eligible_for_lt.add(vehicle_path)
        backup_path = os.path.join(vehicle_path, *self.BACKUPS_SUBDIR, file_name)
        os.makedirs(backup_path, exist_ok=True)

        # Backup the BRV
        new_brv_path = os.path.join(backup_path, "Vehicle.brv")
        shutil.copy2(og_brv, new_brv_path)

        # Add a file containing BEI metadata.
        toml_file = os.path.join(backup_path, "bei_metadata.toml")
        with open(toml_file, "w") as f:
            toml_w = tomli_w.dumps({
                "version": self.BACKUP_SYSTEM_VERSION,
                "description": description,
                "time": time_now
            })
            f.write(toml_w)


    def find_all_excess(self, vehicles_path):
        excess_backups = []
        vehicle_pathes = os.listdir(vehicles_path)
        for vehicle in vehicle_pathes:
            vehicle_path = os.path.join(vehicles_path, vehicle)
            if not os.path.isdir(vehicle_path):
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

        backups_root = os.path.join(vehicle_path, *self.BACKUPS_SUBDIR)
        if not os.path.isdir(backups_root):
            return []

        # Path & store upcoming results
        vehicle_backups = os.listdir(backups_root)
        # backups: list[tuple[type, time, size, path]]
        found_backups: list[tuple[str, int, int, str]] = []

        # Sieve through backups
        for backup in vehicle_backups:
            # Get full backup path
            backup_path = os.path.join(backups_root, backup)
            if (not os.path.exists(backup_path)) or (not os.path.isdir(backup_path)):
                continue

            try:
                backup_type, backup_time = backup.split('-', 1)
                backup_time = int(backup_time[ :18])  # It will be a thousand years before we use 19 digits to represent time this way
                backup_size = dir_size(backup_path)
            except ValueError:
                # Not a backup or malformed, skip.
                continue

            # If a short term backup is too old, then it must be excess
            if backup_type == "st" and deletion_thresold > backup_time:
                excess_backups.append(backup_path)
                # Else add to list to be sorted youngest-oldest
            else:
                found_backups.append((backup_type, backup_time, backup_size, backup_path))

        # We now have the list of backups. Sort from newest to oldest, then prepare variables
        found_backups.sort(key=lambda x: x[1], reverse=True)
        count = {"st": 0, "lt": 0}  # I'm too lazy to make if statements. Hey, if we ever add mid-term...
        size = {"st": 0, "lt": 0}
        max_count = {
            "st": self.main_window.settings.st_backup_count_limit,
            "lt": self.main_window.settings.lt_backup_count_limit
        }
        max_size = {
            "st": self.main_window.settings.st_backup_size_limit_kb * 1024,
            "lt": self.main_window.settings.lt_backup_size_limit_kb * 1024
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
