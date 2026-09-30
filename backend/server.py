"""
backend/server.py

HTTP Server providing REST API endpoints and static web asset hosting for the Refrigerator Control GUI.
Supports FastAPI/uvicorn if installed, with a built-in stdlib http.server fallback.
"""

import os
import sys
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.simulation_engine import SimulationEngine

engine = SimulationEngine()
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gui", "static")


class RefrigerationRequestHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler for Refrigerator Control System backend."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json_response(self, data: dict, status_code: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/state":
            state = engine.get_current_state()
            state["history"] = {
                "time_s": engine.history["time_s"][-200:],
                "temperature_degc": engine.history["temperature_degc"][-200:],
                "setpoint_degc": engine.history["setpoint_degc"][-200:],
                "door_open": engine.history["door_open"][-200:],
                "cooling_power_w": engine.history["cooling_power_w"][-200:],
            }
            state["metrics"] = engine.get_metrics()
            self._send_json_response(state)
        elif path == "/api/metrics":
            metrics = engine.get_metrics()
            self._send_json_response(metrics)
        elif path == "/api/export_csv":
            filepath = engine.intelligent_assistant.event_logger.export_to_csv()
            self._send_json_response({"filepath": filepath, "message": "Exported to CSV successfully"})
        elif path == "/api/batch_results":
            df = engine.run_full_simulation()
            self._send_json_response(df.to_dict(orient="list"))
        else:
            # Default to static file server (serving index.html, JS, CSS)
            super().do_GET()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = (
            json.loads(self.rfile.read(content_length).decode("utf-8"))
            if content_length > 0
            else {}
        )

        if path == "/api/door":
            is_open = post_data.get("door_open", None)
            if is_open is not None:
                engine.set_door_state(bool(is_open))
            else:
                engine.toggle_door()
            state = engine.get_current_state()
            self._send_json_response(state)

        elif path == "/api/step":
            dt_s = post_data.get("dt_s", 1.0)
            steps = post_data.get("steps", 1)
            last_state = {}
            for _ in range(steps):
                last_state = engine.step(dt_s=dt_s)
            self._send_json_response(last_state)

        elif path == "/api/config":
            controller = post_data.get("controller_type")
            setpoint = post_data.get("setpoint_degc")
            ambient = post_data.get("ambient_degc")
            ua_door = post_data.get("ua_door_extra_w_per_k")

            if controller:
                engine.set_controller(controller)
            engine.update_parameters(
                setpoint_degc=setpoint,
                ambient_degc=ambient,
                ua_door_extra_w_per_k=ua_door,
            )
            self._send_json_response(engine.get_current_state())

        elif path == "/api/reset":
            c_type = post_data.get("controller_type", engine.controller_type)
            engine.reset(controller_type=c_type)
            self._send_json_response(engine.get_current_state())

        elif path == "/api/alarm_mute":
            is_muted = post_data.get("is_muted", None)
            if is_muted is not None:
                engine.intelligent_assistant.alert_manager.set_mute(bool(is_muted))
            else:
                engine.intelligent_assistant.alert_manager.toggle_mute()
            self._send_json_response(engine.get_current_state())

        elif path == "/api/export_csv":
            filepath = engine.intelligent_assistant.event_logger.export_to_csv()
            self._send_json_response({"filepath": filepath, "message": "Exported to CSV successfully"})

        elif path == "/api/run_batch":
            controller = post_data.get("controller_type", "pid")
            duration_s = post_data.get("duration_s", 12000.0)
            engine.reset(controller_type=controller)
            df = engine.run_full_simulation(duration_s=duration_s)
            metrics = engine.get_metrics()
            self._send_json_response(
                {"history": df.to_dict(orient="list"), "metrics": metrics}
            )
        else:
            self._send_json_response({"error": "Unknown endpoint"}, status_code=404)


def start_server(host: str = "127.0.0.1", port: int = 8000):
    server = HTTPServer((host, port), RefrigerationRequestHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    start_server()
