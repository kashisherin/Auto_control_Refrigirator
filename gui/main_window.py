"""
gui/main_window.py

PySide6 Desktop Application launcher for Refrigerator Control System.
Opens the classy dashboard interface inside a desktop application window using PySide6.
"""

import sys
import threading
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

import webbrowser
from backend.server import start_server


class MainWindow(QMainWindow):
    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        super().__init__()
        self.setWindowTitle("Predictive Adaptive Refrigeration Control System")
        self.resize(1400, 900)

        if HAS_WEBENGINE:
            self.browser = QWebEngineView()
            self.browser.setUrl(QUrl(server_url))
            self.setCentralWidget(self.browser)
        else:
            webbrowser.open(server_url)


def launch_gui(port: int = 8000):
    """Start backend server in background thread and launch desktop PySide6 UI."""
    server_thread = threading.Thread(
        target=start_server, kwargs={"host": "127.0.0.1", "port": port}, daemon=True
    )
    server_thread.start()

    app = QApplication(sys.argv)
    window = MainWindow(f"http://127.0.0.1:{port}")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_gui()
