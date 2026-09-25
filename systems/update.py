from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QThread, QUrl, Signal
from urllib.request import urlopen
import json
from packaging.version import Version
import logging

_logger = logging.getLogger(__name__)

class UpdateChecker(QThread):
    update_available = Signal(str)
    error = Signal(str)

    def __init__(self, owner, repo, current_version):
        super().__init__()
        self.owner = owner
        self.repo = repo
        self.current_version = current_version
        self.latest_version: str | None = None
        self.error_reason: str | None = None

    def has_known_update(self) -> bool:
        """Whether a newer release than the current version has been found so far.
        Only reliable after the check has finished (see update_available/error signals)."""
        return self.latest_version is not None

    def run(self):
        try:
            _logger.info("Checking for updates...")
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"

            with urlopen(url, timeout=10) as r:
                data = json.load(r)

            latest = data["tag_name"].lstrip("v")

            if Version(latest) > Version(self.current_version):
                _logger.info(f"Update found and available: {latest}")
                self.latest_version = latest
                self.update_available.emit(latest)

        except Exception as e:
            self.error_reason = str(e)
            self.error.emit(self.error_reason)

    def get_download_page(self):
        return f"https://github.com/{self.owner}/{self.repo}/releases/latest"

    def open_download_page(self):
        QDesktopServices.openUrl(QUrl(self.get_download_page()))
