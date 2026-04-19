import atexit, os, signal, socket, subprocess, sys, threading, time, webbrowser
from pathlib import Path
from flask import Flask, jsonify, render_template, request
import setup.builder as builder

REPO_ROOT = Path(__file__).resolve().parent.parent

app = Flask(__name__, template_folder='templates', static_folder='static')

# Port used by the running server; set in main() before app.run().
_port = None
_wizard_state = {}


def find_free_port(preferred: int = 7331) -> int:
    """Return preferred port if free, otherwise return an OS-assigned port.

    Never returns 5000 or 8080.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('127.0.0.1', preferred))
            return sock.getsockname()[1]
        except OSError:
            sock.bind(('', 0))
            return sock.getsockname()[1]


def wait_for_port(port: int, timeout: float = 5.0) -> None:
    """Block until a TCP listener appears on 127.0.0.1:port or timeout expires.

    Raises RuntimeError if the port is not reachable within *timeout* seconds.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"Port {port} not reachable after {timeout}s")


def check_write_permission(project_root: Path) -> bool:
    """Return True if *project_root* is writable by the current process."""
    return os.access(project_root, os.W_OK)


def open_browser_after_ready(url: str, port: int) -> None:
    """Start a daemon thread that opens *url* once the server is accepting connections."""

    def _open():
        try:
            wait_for_port(port)
        except RuntimeError:
            return
        if sys.platform == 'darwin':
            subprocess.Popen(['open', url])
        else:
            webbrowser.open(url)

    t = threading.Thread(target=_open, daemon=True)
    t.start()


def _shutdown_server() -> None:
    # Brief delay lets the /exit response flush before SIGINT fires.
    # Do NOT call server.shutdown() from inside a request handler — that deadlocks Werkzeug.
    time.sleep(0.3)
    os.kill(os.getpid(), signal.SIGINT)


def _cleanup() -> None:
    print("\nSetup wizard exited cleanly.", flush=True)


@app.route('/')
def index():
    return render_template('index.html', port=_port, active_step='gmail')


@app.route('/validate-form', methods=['POST'])
def validate_form():
    data = request.get_json(force=True) or {}
    errors = builder.validate(data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    _wizard_state.update(data)
    env_str, yaml_str = builder.build(_wizard_state)
    return jsonify({"ok": True, "env_preview": env_str, "yaml_preview": yaml_str})


@app.route('/exit', methods=['POST'])
def exit_wizard():
    threading.Thread(target=_shutdown_server, daemon=True).start()
    return jsonify({"ok": True})


def main():
    global _port

    if not check_write_permission(REPO_ROOT):
        print(
            f"ERROR: Project directory {REPO_ROOT} is not writable. "
            "Cannot start setup wizard.",
            file=sys.stderr,
        )
        sys.exit(1)

    _port = find_free_port()
    url = f"http://127.0.0.1:{_port}/"
    atexit.register(_cleanup)
    signal.signal(signal.SIGTERM, lambda s, f: _shutdown_server())
    open_browser_after_ready(url, _port)
    # threaded=False: single-user local wizard; avoids block_on_close keep-alive delay on SIGINT
    app.run(host='127.0.0.1', port=_port, debug=False, use_reloader=False, threaded=False)


if __name__ == '__main__':
    main()
