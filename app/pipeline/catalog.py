import json
from dataclasses import dataclass
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
APP_HOME = PACKAGE_DIR.parent
DEFAULT_MANIFEST_PATH = PACKAGE_DIR / "manifest.json"


@dataclass(frozen=True)
class StageSpec:
    key: str
    order: int
    label: str
    description: str
    script_path: Path
    args: tuple[str, ...]
    inputs: tuple[Path, ...]
    outputs: tuple[Path, ...]

    def to_dict(self):
        return {
            "key": self.key,
            "order": self.order,
            "label": self.label,
            "description": self.description,
            "script_path": str(self.script_path),
            "args": list(self.args),
            "inputs": [str(path) for path in self.inputs],
            "outputs": [str(path) for path in self.outputs],
        }


def _load_json(path: Path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _find_workspace_root():
    for candidate in [APP_HOME.parent, *APP_HOME.parents]:
        if (candidate / "app").exists() and (candidate / "config").exists() and (candidate / "data").exists():
            return candidate
    raise ValueError("Kunde inte hitta workspace root med mapparna app/, config/ och data/.")


WORKSPACE_ROOT = _find_workspace_root()


def _resolve_path(relative_path: str) -> Path:
    return (WORKSPACE_ROOT / relative_path).resolve()


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH):
    path = Path(path)
    manifest = _load_json(path)
    stage_order = manifest.get("stage_order", [])
    stages = manifest.get("stages", {})

    if not stage_order:
        raise ValueError("Manifest saknar stage_order.")
    if not stages:
        raise ValueError("Manifest saknar stages.")
    if len(stage_order) != len(set(stage_order)):
        raise ValueError("Manifest stage_order innehaller dubbletter.")

    missing = [stage_key for stage_key in stage_order if stage_key not in stages]
    if missing:
        raise ValueError(f"Manifest stage_order refererar till okanda steg: {missing}")

    required_stage_fields = {"label", "description", "script"}
    for stage_key, raw_stage in stages.items():
        missing_fields = sorted(required_stage_fields - set(raw_stage))
        if missing_fields:
            raise ValueError(
                f"Manifest steg {stage_key} saknar obligatoriska falt: {', '.join(missing_fields)}"
            )

    return manifest


def load_stage_specs(path: Path = DEFAULT_MANIFEST_PATH):
    path = Path(path)
    manifest = load_manifest(path)
    specs = []

    for order, stage_key in enumerate(manifest["stage_order"], start=1):
        raw_stage = manifest["stages"][stage_key]
        script_path = _resolve_path(raw_stage["script"])
        if not script_path.exists():
            raise ValueError(f"Saknar script for {stage_key}: {script_path}")

        specs.append(
            StageSpec(
                key=stage_key,
                order=order,
                label=raw_stage["label"],
                description=raw_stage["description"],
                script_path=script_path,
                args=tuple(raw_stage.get("args", [])),
                inputs=tuple(_resolve_path(item) for item in raw_stage.get("inputs", [])),
                outputs=tuple(_resolve_path(item) for item in raw_stage.get("outputs", [])),
            )
        )

    return specs


def build_stage_map(path: Path = DEFAULT_MANIFEST_PATH):
    path = Path(path)
    specs = load_stage_specs(path)
    return {spec.key: spec for spec in specs}
