import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .catalog import APP_HOME, DEFAULT_MANIFEST_PATH, WORKSPACE_ROOT, load_stage_specs


REPORTS_DIR = WORKSPACE_ROOT / "data" / "reports" / "pipeline"


@dataclass
class StageRunResult:
    key: str
    label: str
    command: list[str]
    status: str
    duration_seconds: float
    return_code: int | None
    missing_inputs: list[str]
    stdout: str
    stderr: str

    def to_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "command": self.command,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 3),
            "return_code": self.return_code,
            "missing_inputs": self.missing_inputs,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def _now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def _parse_stage_args(values):
    if not values:
        return []

    parsed = []
    for value in values:
        parsed.extend(part.strip() for part in value.split(",") if part.strip())
    return parsed


def _select_stage_specs(stage_specs, only=None, start=None, end=None, skip=None):
    only = _parse_stage_args(only)
    skip = set(_parse_stage_args(skip))
    stage_keys = [spec.key for spec in stage_specs]
    stage_map = {spec.key: spec for spec in stage_specs}

    unknown = [
        key
        for key in only + list(skip) + [item for item in [start, end] if item]
        if key not in stage_map
    ]
    if unknown:
        raise ValueError(f"Okanda steg: {sorted(set(unknown))}")

    if only:
        selected = [stage_map[key] for key in stage_keys if key in only]
    else:
        start_index = stage_keys.index(start) if start else 0
        end_index = stage_keys.index(end) if end else len(stage_keys) - 1
        if start_index > end_index:
            raise ValueError("--from kommer efter --to. Byt ordning eller ange ett mindre spann.")
        selected = stage_specs[start_index:end_index + 1]

    selected = [spec for spec in selected if spec.key not in skip]
    if not selected:
        raise ValueError("Inga steg valdes att koera.")

    return selected


def _build_command(spec):
    return [sys.executable, str(spec.script_path), *spec.args]


def _find_missing_inputs(spec):
    return [str(path) for path in spec.inputs if not path.exists()]


def _run_single_stage(spec, dry_run=False):
    command = _build_command(spec)
    missing_inputs = _find_missing_inputs(spec)

    if missing_inputs:
        return StageRunResult(
            key=spec.key,
            label=spec.label,
            command=command,
            status="missing_inputs",
            duration_seconds=0.0,
            return_code=None,
            missing_inputs=missing_inputs,
            stdout="",
            stderr="Ett eller flera input saknas for steget.",
        )

    if dry_run:
        return StageRunResult(
            key=spec.key,
            label=spec.label,
            command=command,
            status="dry_run",
            duration_seconds=0.0,
            return_code=None,
            missing_inputs=[],
            stdout="",
            stderr="",
        )

    started_at = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    duration_seconds = time.perf_counter() - started_at

    return StageRunResult(
        key=spec.key,
        label=spec.label,
        command=command,
        status="ok" if completed.returncode == 0 else "failed",
        duration_seconds=duration_seconds,
        return_code=completed.returncode,
        missing_inputs=[],
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_pipeline(manifest_path=DEFAULT_MANIFEST_PATH, only=None, start=None, end=None, skip=None, dry_run=False, continue_on_error=False):
    stage_specs = load_stage_specs(manifest_path)
    selected_specs = _select_stage_specs(stage_specs, only=only, start=start, end=end, skip=skip)
    results = []

    for spec in selected_specs:
        result = _run_single_stage(spec, dry_run=dry_run)
        results.append(result)

        if result.status == "failed" and not continue_on_error:
            break

    report = {
        "generated_at_utc": _now_utc_iso(),
        "manifest_path": str(Path(manifest_path).resolve()),
        "workspace_root": str(WORKSPACE_ROOT),
        "app_home": str(APP_HOME),
        "dry_run": dry_run,
        "continue_on_error": continue_on_error,
        "selected_stage_keys": [spec.key for spec in selected_specs],
        "completed_stage_keys": [result.key for result in results],
        "all_successful": all(result.status in {"ok", "dry_run"} for result in results) and len(results) == len(selected_specs),
        "results": [result.to_dict() for result in results],
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_report_path = REPORTS_DIR / f"pipeline_run_{timestamp}.json"
    latest_report_path = REPORTS_DIR / "latest_run.json"
    report["report_paths"] = {
        "timestamped": str(timestamped_report_path),
        "latest": str(latest_report_path),
    }
    _write_json(timestamped_report_path, report)
    _write_json(latest_report_path, report)

    return report
