#!/usr/bin/env python3
"""
AI File Sorter - Launcher
Run this script to start the app.
"""

import os
import sys
import subprocess
import platform
import webbrowser
import time

if getattr(sys, 'frozen', False):
    ROOT = sys._MEIPASS
else:
    ROOT = os.path.dirname(os.path.abspath(__file__))

BACKEND = os.path.join(ROOT, "backend")
REQ = os.path.join(ROOT, "requirements.txt")


def install_deps():
    print("📦 Installing Python dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQ, "--quiet"])
    print("✅ Dependencies installed.\n")


def check_ollama():
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        print("✅ Ollama is running.\n")
        return True
    except Exception:
        print("⚠️  Ollama not detected at localhost:11434")
        print("   Make sure Ollama is running: https://ollama.com")
        print("   And that you have gemma2:2b pulled: ollama pull gemma2:2b\n")
        return False


def main():
    print("=" * 50)
    print("  🗂  AI File Sorter")
    print("=" * 50)
    print()

    # Install dependencies if needed
    try:
        import flask
        import fitz
    except ImportError:
        install_deps()

    check_ollama()

    print("🚀 Starting web UI at http://localhost:7432")
    print("   Press Ctrl+C to stop.\n")

    sys.path.insert(0, BACKEND)
    os.chdir(BACKEND)

    import threading
    threading.Timer(1.5, lambda: webbrowser.open("http://localhost:7432")).start()

    from server import app
    app.run(host="0.0.0.0", port=7432, debug=False)


if __name__ == "__main__":
    main()
