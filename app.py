from flask import Flask, render_template, request, send_file, redirect, url_for
from datetime import datetime
import os
import json
import subprocess

app = Flask(__name__)

LOG_FILE = "logs.json"
CSV_PATH = "events_for_upload.csv"

def log_run(mode, status):
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    logs.insert(0, {
        "mode": mode,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status
    })
    with open(LOG_FILE, "w") as f:
        json.dump(logs[:10], f)  # keep only 10 most recent

@app.route("/")
def dashboard():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    return render_template("index.html", logs=logs, csv_exists=os.path.exists(CSV_PATH))

@app.route("/scrape", methods=["POST"])
def scrape():
    mode = request.form.get("mode", "weekly")
    try:
        result = subprocess.run(["python3", "main.py", mode], capture_output=True, text=True, timeout=120)
        print(result.stdout)
        log_run(mode, "success" if result.returncode == 0 else "error")
    except Exception as e:
        log_run(mode, f"error: {e}")
    return redirect(url_for("dashboard"))

@app.route("/download")
def download_csv():
    if os.path.exists(CSV_PATH):
        return send_file(CSV_PATH, as_attachment=True)
    return "No CSV found", 404

if __name__ == "__main__":
    app.run(debug=True)
