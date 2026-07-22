import os
import threading
import webbrowser
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))


def open_browser():
    webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    # Flask's debug reloader restarts this script in a child process, which
    # would open a second browser tab. WERKZEUG_RUN_MAIN is only set in that
    # child, so this guard makes sure the browser opens exactly once.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.0, open_browser).start()
    app.run(debug=True)