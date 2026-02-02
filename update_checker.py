from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QThread, QUrl, Signal
import requests
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

    def run(self):
        try:
            _logger.info("Checking for updates...")
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"
            r = requests.get(url, timeout=10)
            r.raise_for_status()

            latest = r.json()["tag_name"].lstrip("v")

            if Version(latest) > Version(self.current_version):
                _logger.info(f"Update found and available: {latest}")
                self.update_available.emit(latest)

        except Exception as e:
            # Silently fail or log — users don’t need to see this
            self.error.emit(str(e))

    def get_download_page(self):
        return f"https://github.com/{self.owner}/{self.repo}/releases/latest"

    def open_download_page(self):
        QDesktopServices.openUrl(QUrl(self.get_download_page()))
