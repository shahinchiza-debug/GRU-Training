import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_STAGE2_VALID_DIR = WORKSPACE_ROOT / "data" / "output" / "stage02_filter" / "valid_templates"
DEFAULT_STAGE3_DIR = WORKSPACE_ROOT / "data" / "output" / "stage03_split"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def get_deviation_count(template):
    validation = template.get("_validation", {})
    derived = validation.get("derived", {})
    count = derived.get("deviation_count")
    if count is not None:
        return count

    d1_active = template.get("D_1", {}).get("state") is not None
    d2_active = template.get("D_2", {}).get("state") is not None
    return int(d1_active) + int(d2_active)


def clear_previous_outputs(output_dirs, report_paths):
    for directory in output_dirs:
        for existing_file in directory.glob("RAW_*.json"):
            existing_file.unlink()

    for report_path in report_paths:
        if report_path.exists():
            report_path.unlink()


def main():
    parser = argparse.ArgumentParser(
        description="Split valid stage-2 templates into 0D, 1D and 2D groups for stage 3."
    )
    parser.add_argument(
        "--indir",
        default=str(DEFAULT_STAGE2_VALID_DIR),
        help="Directory containing valid RAW_*.json templates from stage 2.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_STAGE3_DIR),
        help="Directory for stage-3 output.",
    )
    args = parser.parse_args()

    indir = Path(args.indir)
    outdir = Path(args.outdir)
    del_1_0d_dir = outdir / "del_1_0d"
    del_2_1d_dir = outdir / "del_2_1d"
    del_3_2d_dir = outdir / "del_3_2d"

    outdir.mkdir(parents=True, exist_ok=True)
    del_1_0d_dir.mkdir(parents=True, exist_ok=True)
    del_2_1d_dir.mkdir(parents=True, exist_ok=True)
    del_3_2d_dir.mkdir(parents=True, exist_ok=True)

    report_path = outdir / "stage3_split_report.json"
    metadata_path = outdir / "stage3_metadata.json"
    clear_previous_outputs(
        [del_1_0d_dir, del_2_1d_dir, del_3_2d_dir],
        [report_path, metadata_path],
    )

    template_paths = sorted(indir.glob("RAW_*.json"))
    if not template_paths:
        raise ValueError(f"Inga RAW_*.json-filer hittades i {indir}")

    distribution = Counter()
    output_map = {
        0: del_1_0d_dir,
        1: del_2_1d_dir,
        2: del_3_2d_dir,
    }

    for template_path in template_paths:
        template = load_json(template_path)
        deviation_count = get_deviation_count(template)

        if deviation_count not in output_map:
            raise ValueError(
                f"Ogiltigt deviation_count i {template_path.name}: {deviation_count}. Förväntat 0, 1 eller 2."
            )

        target_dir = output_map[deviation_count]
        shutil.copy2(template_path, target_dir / template_path.name)
        distribution[deviation_count] += 1

    report_payload = {
        "processed_template_count": len(template_paths),
        "distribution": {
            "del_1_0d": distribution[0],
            "del_2_1d": distribution[1],
            "del_3_2d": distribution[2],
        },
    }
    write_json(report_path, report_payload)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(indir),
        "output_directory": str(outdir),
        "processed_template_count": len(template_paths),
        "distribution": {
            "del_1_0d": distribution[0],
            "del_2_1d": distribution[1],
            "del_3_2d": distribution[2],
        },
    }
    write_json(metadata_path, metadata_payload)

    print(
        f"Stage 3 complete. Processed {len(template_paths)} templates: "
        f"0D={distribution[0]}, 1D={distribution[1]}, 2D={distribution[2]}."
    )


if __name__ == "__main__":
    main()
