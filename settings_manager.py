import tomllib, tomli_w
from pathlib import Path
from platformdirs import user_config_dir
import sys

from PySide6.QtWidgets import QMessageBox


class SettingsManager:

    APP_NAME = "BrickEditInterface"
    SAVE_FILE = "settings.toml"
    CURRENT_FILE_VERSION = 0
    
    def __init__(self):
        self.create_default_settings()
        self.load()

    def create_default_settings(self):
        self.short_term_backup_limit = 6
        self.long_term_backup_limit = 3


    def get_settings_path(self):
        config_dir = Path(user_config_dir(self.APP_NAME))
        settings_file = config_dir / self.SAVE_FILE

        config_dir.mkdir(parents=True, exist_ok=True)

        if not settings_file.exists():
            return None

        return settings_file


    def save(self):
        settings = {
            "file_version": self.CURRENT_FILE_VERSION,
            "short_term_backup_limit": self.short_term_backup_limit,
            "long_term_backup_limit": self.long_term_backup_limit,
        }
        # Make sure the path exist. We don't do anything of the result
        settings_path = self.get_settings_path()
        # Save
        with open(settings_path, "wb") as f:
            tomli_w.dump(settings, f)

    def load(self):
        settings_path = self.get_settings_path()
        if settings_path is None:
            return
        try:
            with open(settings_path, "rb") as f:
                settings = tomllib.load(f)

                file_version = settings.get("file_version", -1)
                self.short_term_backup_limit = settings.get("short_term_backup_limit", self.short_term_backup_limit)
                self.long_term_backup_limit = settings.get("long_term_backup_limit", self.long_term_backup_limit)

                if file_version > self.CURRENT_FILE_VERSION or file_version == -1:
                    QMessageBox.warning("Unknown file version", "The settings file you are loading may contain error. Please try to update BrickEdit-Interface.")

        except Exception as e:
            dlg = QMessageBox(QMessageBox.Critical, "Error")
            dlg.setText(f"""\
Failed to load user settings!
Please report the following error to the author: {type(e).__name__}: {e}.

Press Cancel to close BrickEdit-Interface.
If you press OK, you may reset your settings!
""")
            dlg.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
            dlg.setDefaultButton(QMessageBox.Cancel)
            result = dlg.exec()

            if result == QMessageBox.Ok:
                pass
            else:
                sys.exit(1)
