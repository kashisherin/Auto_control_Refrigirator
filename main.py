"""
main.py

Main launcher for the Refrigerator Control System.
Launches the backend physical simulation engine and opens the classy user interface.

Usage:
    python main.py             # Launches full system with UI in browser
    python main.py --desktop   # Launches PySide6 desktop window
"""

import argparse
import threading
import time
import webbrowser
from backend.server import start_server


def main():
    parser = argparse.ArgumentParser(description="Refrigeration Control System UI & Backend")
    parser.add_argument("--desktop", action="store_true", help="Launch native PySide6 desktop GUI window")
    parser.add_argument("--port", type=int, default=8000, help="Port for backend server (default: 8000)")
    args = parser.parse_args()

    if args.desktop:
        from gui.main_window import launch_gui
        launch_gui(port=args.port)
    else:
        server_thread = threading.Thread(
            target=start_server,
            kwargs={"host": "127.0.0.1", "port": args.port},
            daemon=True
        )
        server_thread.start()
        time.sleep(1.0)
        url = f"http://127.0.0.1:{args.port}"
        print(f"\nRefrigerator Control Dashboard is live at: {url}")
        webbrowser.open(url)
        server_thread.join()


if __name__ == "__main__":
    main()
