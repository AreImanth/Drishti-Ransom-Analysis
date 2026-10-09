"""Build a Regshot-style comparison file from baseline/post snapshots.

Replaces the manual Regshot Shot-1/Shot-2 GUI step on headless systems
(e.g. Docker on a Linux server, where there is no Windows registry and no
GUI). Diffs evidence/baseline/baseline_files.json against
evidence/post/post_attack_files.json and writes
evidence/post/regshot_comparison.txt in the same "Files added:" /
"Files deleted:" format that report_data.py already parses, so the HTML
report's Regshot tab works unchanged.

Usage:
    python analysis/build_comparison.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab_paths import BASELINE_DIR, POST_DIR  # noqa: E402

BASELINE = BASELINE_DIR / "baseline_files.json"
POST = POST_DIR / "post_attack_files.json"
OUTPUT = POST_DIR / "regshot_comparison.txt"


def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_comparison(baseline_path=None, post_path=None, out_path=None) -> dict:
    """Diff two file-snapshot JSONs and write a comparison file.

    Returns {"added": [...], "deleted": [...], "output": str}.
    Raises FileNotFoundError if a snapshot is missing.
    """
    baseline_path = Path(baseline_path) if baseline_path else BASELINE
    post_path = Path(post_path) if post_path else POST
    out_path = Path(out_path) if out_path else OUTPUT

    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline snapshot not found: {baseline_path}")
    if not post_path.exists():
        raise FileNotFoundError(f"Post-attack snapshot not found: {post_path}")

    baseline = load(baseline_path)
    post = load(post_path)

    before = {item["path"] for item in baseline}
    after = {item["path"] for item in post}

    # NOTE: report_data.py parses each section by taking splitlines()[2:200],
    # i.e. it skips the section-title line plus exactly one following line.
    # Keep that layout: title line, one separator line, then paths.
    added = sorted(after - before)
    deleted = sorted(before - after)

    stamp = datetime.now(timezone.utc).isoformat()
    lines = [
        "Lab snapshot comparison (auto-generated, no Regshot needed)",
        f"Generated: {stamp}",
        f"Baseline: {baseline_path} ({len(baseline)} files)",
        f"Post-attack: {post_path} ({len(post)} files)",
        "",
        f"Files added: {len(added)}",
        "----------------------------------",
        *added,
        "",
        f"Files deleted: {len(deleted)}",
        "----------------------------------",
        *deleted,
        "",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    return {"added": added, "deleted": deleted, "output": str(out_path)}


def main() -> int:
    try:
        result = build_comparison()
    except FileNotFoundError as exc:
        print(f"[!] {exc}")
        return 1
    print("=" * 60)
    print("SNAPSHOT COMPARISON (AUTO)")
    print("=" * 60)
    print(f"Files added   : {len(result['added'])}")
    print(f"Files deleted : {len(result['deleted'])}")
    print(f"Output        : {result['output']}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
