"""
Flask server for AI File Sorter
Serves the UI and exposes REST endpoints for sorting.
"""

import os
import sys
import json
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

# Add parent dir so we can import sorter
sys.path.insert(0, os.path.dirname(__file__))
from sorter import sort_files, extract_text_from_file

app = Flask(__name__, static_folder="../frontend")

# ── In-memory job store ───────────────────────────────────────────────────────
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def new_job_id() -> str:
    import uuid
    return str(uuid.uuid4())[:8]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


@app.route("/api/check-ollama", methods=["GET"])
def check_ollama():
    """Check if Ollama is running and which models are available."""
    import urllib.request
    url = request.args.get("url", "http://localhost:11434")
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return jsonify({"ok": True, "models": models})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "models": []})


@app.route("/api/sort", methods=["POST"])
def start_sort():
    """Start a sort job. Body: {files, output_dir, model, ollama_url, copy_mode}"""
    body = request.json or {}
    files = body.get("files", [])
    folder_path = body.get("folder_path", "")
    output_dir = body.get("output_dir", "")
    model = body.get("model", "gemma2:2b")
    ollama_url = body.get("ollama_url", "http://localhost:11434")
    copy_mode = body.get("copy_mode", True)

    # If folder path given, scan it for files
    if not files and folder_path:
        if not os.path.isdir(folder_path):
            return jsonify({"error": f"Folder not found: {folder_path}"}), 400
        from sorter import scan_folder
        files = scan_folder(folder_path)

    if not files:
        return jsonify({"error": "No files provided"}), 400

    if not output_dir:
        if folder_path and os.path.isdir(folder_path):
            output_dir = os.path.join(os.path.abspath(folder_path), "sorted")
        else:
            parent_dirs = {os.path.dirname(os.path.abspath(f)) for f in files}
            if len(parent_dirs) == 1:
                output_dir = os.path.join(parent_dirs.pop(), "sorted")
            else:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                output_dir = os.path.join(desktop, "sorted")

    # Validate paths exist
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        return jsonify({"error": f"Files not found: {missing[:3]}"}), 400

    os.makedirs(output_dir, exist_ok=True)

    job_id = new_job_id()
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "running",
            "total": len(files),
            "done": 0,
            "output_dir": output_dir,
            "current_file": None,
            "current_status": None,
            "results": [],
            "started_at": time.time(),
            "finished_at": None,
            "error": None
        }

    def progress_cb(i, total, filename, status, result):
        with jobs_lock:
            job = jobs[job_id]
            job["current_file"] = filename
            job["current_status"] = status
            if status in ("done", "error") and result:
                job["results"].append(result)
                job["done"] += 1

    def run():
        try:
            sort_files(
                filepaths=files,
                output_dir=output_dir,
                model=model,
                ollama_url=ollama_url,
                copy_mode=copy_mode,
                progress_callback=progress_cb
            )
        except Exception as e:
            with jobs_lock:
                jobs[job_id]["error"] = str(e)
        finally:
            with jobs_lock:
                jobs[job_id]["status"] = "done"
                jobs[job_id]["finished_at"] = time.time()

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/job/<job_id>", methods=["GET"])
def get_job(job_id):
    """Poll job status."""
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/select-files", methods=["GET"])
def select_files():
    """Open a native OS file dialog to select files and return their absolute paths."""
    import tkinter as tk
    from tkinter import filedialog
    
    # Create a hidden tk root window
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    
    # Open the file selection dialog
    file_paths = filedialog.askopenfilenames(
        title="Select files to sort",
        parent=root
    )
    
    # Destroy the root window
    root.destroy()
    
    return jsonify({"files": list(file_paths)})


@app.route("/api/preview", methods=["POST"])
def preview_file():
    """Get a text preview of a file (for UI display)."""
    body = request.json or {}
    filepath = body.get("path", "")
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    text = extract_text_from_file(filepath, max_chars=500)
    return jsonify({"preview": text})


@app.route("/api/open-folder", methods=["POST"])
def open_folder():
    """Open a folder natively in the OS file explorer."""
    body = request.json or {}
    folder_path = body.get("path", "")
    if folder_path and os.path.exists(folder_path):
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder_path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder_path])
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Folder not found"}), 404


# ── Watchdog ──────────────────────────────────────────────────────────────────
last_ping_time = time.time()

@app.route("/api/ping", methods=["POST"])
def ping():
    global last_ping_time
    last_ping_time = time.time()
    return jsonify({"ok": True})

def watchdog():
    global last_ping_time
    # 15 second grace period on startup for browser to launch
    time.sleep(15)
    while True:
        time.sleep(2)
        # If no ping received in the last 6 seconds, the UI was closed
        if time.time() - last_ping_time > 6:
            import os
            os._exit(0)

if __name__ == "__main__":
    import webbrowser
    port = 7432
    print(f"\n🗂  AI File Sorter starting...")
    print(f"   Opening at: http://localhost:{port}\n")
    
    # Start the watchdog to terminate when UI is closed
    threading.Thread(target=watchdog, daemon=True).start()
    
    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=False)
