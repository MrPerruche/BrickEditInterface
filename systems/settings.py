import tomllib, tomli_w
from pathlib import Path
from platformdirs import user_config_dir
from sys import exit as sys_exit


class SettingsManagerV2:

    APP_NAME = "BrickEditInterface"
    SAVE_FILE = "settings.toml"
    CURRENT_FILE_VERSION = 0

    def __init__(self):
        self.defaults = {}
        self.settings = {}
        self.register('file_version', SettingsManagerV2.CURRENT_FILE_VERSION)

    # --- API ---

    def register(self, name: str, default):
        self.defaults[name] = default

    def get(self, name: str, fallback = None):
        """Fallbacks typically should be pointless unless you are retrieving unregistered settings."""
        return self.settings[name] if name in self.settings else self.defaults.get(name, fallback)

    def get_default(self, name: str):
        return self.defaults[name]

    def set(self, name: str, value):
        self._set_settings({**self.settings, name: value})

    def reset(self, name: str, must_exist=False):
        if must_exist or name in self.settings:
            del self.settings[name]

    def reset_all(self):
        self.settings = {}

    def get_all_settings(self):
        return self.defaults | self.settings

    # --- PRIVATE STUFF

    def _set_settings(self, settings: dict):
        self.settings = settings
        self.save()

    def _set_defaults(self, defaults: dict):
        self.defaults = defaults

    # --- IO

    def get_settings_path(self, return_none_if_missing=False):
        config_dir = Path(user_config_dir(SettingsManagerV2.APP_NAME))
        settings_file = config_dir / SettingsManagerV2.SAVE_FILE

        config_dir.mkdir(parents=True, exist_ok=True)

        if return_none_if_missing and not settings_file.exists():
            return None

        return settings_file


    def save(self):
        settings = self.get_all_settings()
        settings_path = self.get_settings_path()
        # Save
        with open(settings_path, "wb") as f:
            tomli_w.dump(settings, f)

    def load(self):
        settings_path = self.get_settings_path(True)
        if settings_path is None:
            return
        try:
            with open(settings_path, "rb") as f:
                self._set_settings(tomllib.load(f))
        except Exception as e:
            from ui.dialogs import CorruptSettingsDialog

            dlg = CorruptSettingsDialog.create(self.mw, e)
            result = dlg.exec()
            print(result)
            sys_exit(1)  # TODO only testing


settings_manager = SettingsManagerV2()
