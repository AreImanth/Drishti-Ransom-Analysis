"""
Ransomware Behavior Lab — Web UI

A Flask-based web interface that guides users through the full
attack → detection → forensics pipeline with a click-based workflow.

Usage:
    python webui\app.py
    # Then open http://localhost:6767 in your browser
"""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lab_paths import CONFIG, LAB_ROOT, LOG_DIR, REPORTS_DIR  # noqa: E402

app = Flask(__name__)

# Global state for the attack pipeline
pipeline_state = {
    "phase": "idle",  # idle, baseline, detector, simulator, post, compare, done
    "logs": [],
    "alert": None,
    "comparison": "",
    "comparison_source": None,  # "auto" | "manual" | None
    "snapshot": None,  # {"added": int, "deleted": int} after auto-compare
    "report_path": None,
    "error": None,
}


def run_script(script_name, args=None):
    """Run a Python script and capture output."""
    cmd = [sys.executable, str(PROJECT_ROOT / script_name)]
    if args:
        cmd.extend(args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=300,
    )
    return result.stdout + result.stderr, result.returncode


def run_attack_pipeline():
    """Run the full attack pipeline in a background thread."""
    try:
        pipeline_state["phase"] = "baseline"
        pipeline_state["logs"] = []
        pipeline_state["error"] = None
        pipeline_state["alert"] = None
        pipeline_state["comparison"] = ""
        pipeline_state["comparison_source"] = None
        pipeline_state["snapshot"] = None
        pipeline_state["report_path"] = None

        # Step 0: Reset to a clean pre-attack state. Without this, re-runs
        # find an already-.locked victim folder, the simulator skips every
        # file (0 events, no alert), and the comparison comes out empty.
        pipeline_state["phase"] = "reset"
        pipeline_state["logs"].append("[0/4] Resetting lab to clean state...")
        output, code = run_script("reset_lab.py")
        pipeline_state["logs"].append(output)
        if code != 0:
            pipeline_state["error"] = "Lab reset failed"
            pipeline_state["phase"] = "error"
            return

        # Step 1: Collect baseline
        pipeline_state["logs"].append("[1/4] Collecting baseline...")
        output, code = run_script("analysis/collect_baseline.py")
        pipeline_state["logs"].append(output)
        if code != 0:
            pipeline_state["error"] = "Baseline collection failed"
            pipeline_state["phase"] = "error"
            return

        # Step 2: Start detector
        pipeline_state["phase"] = "detector"
        pipeline_state["logs"].append("[2/4] Starting detector...")
        detector_proc = subprocess.Popen(
            [sys.executable, str(PROJECT_ROOT / "detector/detector.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        time.sleep(2)  # Warmup

        # Step 3: Run simulator
        pipeline_state["phase"] = "simulator"
        pipeline_state["logs"].append("[3/4] Running ransomware simulator...")
        output, code = run_script("simulator/ransomware_simulator.py")
        pipeline_state["logs"].append(output)
        if code != 0:
            pipeline_state["logs"].append("[!] Simulator finished with warnings")

        # Step 4: Stop detector
        pipeline_state["logs"].append("[4/4] Stopping detector...")
        detector_proc.terminate()
        try:
            detector_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            detector_proc.kill()
            detector_proc.wait(timeout=5)

        # Step 5: Collect post-attack baseline
        pipeline_state["phase"] = "post"
        pipeline_state["logs"].append("Collecting post-attack baseline...")
        output, code = run_script("analysis/collect_post.py")
        pipeline_state["logs"].append(output)
        if code != 0:
            pipeline_state["error"] = "Post-attack collection failed"
            pipeline_state["phase"] = "error"
            return

        # Check for alerts
        alerts = sorted(LOG_DIR.glob("ransomware_alert_*.json"))
        if alerts:
            with open(alerts[-1], "r", encoding="utf-8") as f:
                pipeline_state["alert"] = json.load(f)

        # Snapshot 2 + comparison: auto-generated from baseline/post diff,
        # no Regshot needed on headless systems.
        pipeline_state["phase"] = "compare"
        pipeline_state["logs"].append("Building snapshot comparison (auto)...")
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
            import build_comparison

            result = build_comparison.build_comparison()
            pipeline_state["comparison"] = (
                PROJECT_ROOT / "evidence" / "post" / "regshot_comparison.txt"
            ).read_text(encoding="utf-8")
            pipeline_state["snapshot"] = {
                "added": len(result["added"]),
                "deleted": len(result["deleted"]),
            }
            pipeline_state["comparison_source"] = "auto"
            pipeline_state["logs"].append(
                f"[+] Comparison auto-generated: "
                f"{len(result['added'])} added, {len(result['deleted'])} deleted."
            )
        except Exception as exc:
            pipeline_state["logs"].append(
                f"[!] Auto-comparison failed ({exc}) — paste output manually."
            )

        pipeline_state["phase"] = "done"
        pipeline_state["logs"].append("[+] Attack phase complete!")

    except Exception as exc:
        pipeline_state["error"] = str(exc)
        pipeline_state["phase"] = "error"
        pipeline_state["logs"].append(f"[!] Error: {exc}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/logo.png")
def logo():
    from flask import send_from_directory

    return send_from_directory(PROJECT_ROOT / "assets", "logo.png")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "phase": pipeline_state["phase"]})


@app.route("/api/status")
def status():
    return jsonify(pipeline_state)


@app.route("/api/start_attack", methods=["POST"])
def start_attack():
    if pipeline_state["phase"] in (
        "reset",
        "baseline",
        "detector",
        "simulator",
        "post",
        "compare",
    ):
        return jsonify({"error": "Attack already in progress"}), 400

    thread = threading.Thread(target=run_attack_pipeline, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/api/build_comparison", methods=["POST"])
def build_comparison_api():
    """(Re)generate the comparison from baseline/post snapshots."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "analysis"))
        import build_comparison

        result = build_comparison.build_comparison()
        pipeline_state["comparison"] = (
            PROJECT_ROOT / "evidence" / "post" / "regshot_comparison.txt"
        ).read_text(encoding="utf-8")
        pipeline_state["snapshot"] = {
            "added": len(result["added"]),
            "deleted": len(result["deleted"]),
        }
        pipeline_state["comparison_source"] = "auto"
        return jsonify({"status": "done", "snapshot": pipeline_state["snapshot"]})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/comparison", methods=["POST"])
def save_comparison():
    data = request.get_json()
    pipeline_state["comparison"] = data.get("comparison", "")
    pipeline_state["comparison_source"] = "manual"
    pipeline_state["snapshot"] = None
    # Save to evidence/post/regshot_comparison.txt
    post_dir = PROJECT_ROOT / "evidence" / "post"
    post_dir.mkdir(parents=True, exist_ok=True)
    (post_dir / "regshot_comparison.txt").write_text(
        pipeline_state["comparison"], encoding="utf-8"
    )
    return jsonify({"status": "saved"})


@app.route("/api/build_report", methods=["POST"])
def build_report():
    try:
        # Run analysis
        output, code = run_script("analysis/analyze_results.py")
        if code != 0:
            return jsonify({"error": f"Analysis failed: {output}"}), 500

        # Run graphs
        output, code = run_script("analysis/generate_graphs.py")
        if code != 0:
            return jsonify({"error": f"Graph generation failed: {output}"}), 500

        # Build report
        comparison_path = str(PROJECT_ROOT / "evidence" / "post" / "regshot_comparison.txt")
        output, code = run_script(
            "build_report.py", ["--comparison", comparison_path]
        )
        if code != 0:
            return jsonify({"error": f"Report build failed: {output}"}), 500

        # Find the generated report
        reports = sorted(REPORTS_DIR.glob("report_*.html"))
        if not reports:
            return jsonify({"error": "Report file not found"}), 500

        pipeline_state["report_path"] = str(reports[-1])
        pipeline_state["logs"].append(f"[+] Report generated: {reports[-1].name}")

        return jsonify({
            "status": "done",
            "report_path": f"/reports/{reports[-1].name}",
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/reports/<path:filename>")
def view_report(filename):
    from flask import abort, send_from_directory

    if ".." in filename or filename.startswith("/"):
        abort(400)
    return send_from_directory(REPORTS_DIR, filename)


if __name__ == "__main__":
    _port = int(os.environ.get("PORT", "6767"))
    print("=" * 60)
    print("Ransomware Behavior Lab — Web UI")
    print("=" * 60)
    print(f"Project : {PROJECT_ROOT}")
    print(f"Victim  : {LAB_ROOT}")
    print()
    print(f"Open http://localhost:{_port} in your browser")
    print("=" * 60)
    app.run(host="0.0.0.0", port=_port, debug=False)
