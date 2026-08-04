import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_STAGE3_DIR = PROJECT_ROOT / "stage3_output"
DEFAULT_STAGE4_DIR = PROJECT_ROOT / "stage4_output"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "input" / "stage4_turn_distribution.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_template(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_group_dirs(outdir, config):
    group_dirs = {}
    for group_key, group_config in config["groups"].items():
        base_dir = outdir / group_key
        base_dir.mkdir(parents=True, exist_ok=True)
        turn_dirs = {}
        for allocation in group_config["turn_allocations"]:
            turn_dir = base_dir / f"turn_{allocation['turn_count']}"
            turn_dir.mkdir(parents=True, exist_ok=True)
            turn_dirs[allocation["turn_count"]] = turn_dir
        group_dirs[group_key] = turn_dirs
    return group_dirs


def clear_previous_outputs(group_dirs, outdir):
    for turn_dirs in group_dirs.values():
        for directory in turn_dirs.values():
            for existing_file in directory.glob("RAW_*.json"):
                existing_file.unlink()

    for report_name in ["stage4_distribution_report.json", "stage4_metadata.json"]:
        report_path = outdir / report_name
        if report_path.exists():
            report_path.unlink()


def validate_config(config, stage3_dir):
    for group_key, group_config in config["groups"].items():
        expected = group_config["expected_input_count"]
        allocated = sum(item["count"] for item in group_config["turn_allocations"])
        if expected != allocated:
            raise ValueError(
                f"Fel i config för {group_key}: expected_input_count={expected} men turn_allocations summerar till {allocated}."
            )

        source_dir = stage3_dir / group_key
        if not source_dir.exists():
            raise ValueError(f"Saknar källmapp för {group_key}: {source_dir}")


def annotate_template(template, group_key, group_label, turn_count):
    annotated = dict(template)
    annotated["stage4"] = {
        "deviation_group": group_key,
        "deviation_group_label": group_label,
        "turn_count": turn_count,
    }
    return annotated


def main():
    parser = argparse.ArgumentParser(
        description="Distribute stage-3 templates into turn-count buckets for stage 4."
    )
    parser.add_argument(
        "--indir",
        default=str(DEFAULT_STAGE3_DIR),
        help="Directory containing stage-3 split folders.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to stage4_turn_distribution.json.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_STAGE4_DIR),
        help="Directory for stage-4 output.",
    )
    args = parser.parse_args()

    stage3_dir = Path(args.indir)
    config_path = Path(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    config = load_json(config_path)
    validate_config(config, stage3_dir)
    group_dirs = build_group_dirs(outdir, config)
    clear_previous_outputs(group_dirs, outdir)

    totals_by_turn = Counter()
    totals_by_group = {}
    processed_template_count = 0

    for group_key, group_config in config["groups"].items():
        source_dir = stage3_dir / group_key
        template_paths = sorted(source_dir.glob("RAW_*.json"))
        expected_input_count = group_config["expected_input_count"]

        if len(template_paths) != expected_input_count:
            raise ValueError(
                f"Fel antal mallar i {source_dir}. Förväntat {expected_input_count}, hittade {len(template_paths)}."
            )

        index = 0
        group_counter = Counter()

        for allocation in group_config["turn_allocations"]:
            turn_count = allocation["turn_count"]
            count = allocation["count"]
            turn_dir = group_dirs[group_key][turn_count]
            bucket = template_paths[index:index + count]

            if len(bucket) != count:
                raise ValueError(
                    f"Fel bucket-längd för {group_key} turn_{turn_count}. Förväntat {count}, fick {len(bucket)}."
                )

            for template_path in bucket:
                template = load_json(template_path)
                annotated = annotate_template(
                    template,
                    group_key=group_key,
                    group_label=group_config["label"],
                    turn_count=turn_count,
                )
                write_template(turn_dir / template_path.name, annotated)

            index += count
            group_counter[turn_count] += count
            totals_by_turn[turn_count] += count
            processed_template_count += count

        if index != len(template_paths):
            raise ValueError(
                f"Alla mallar i {group_key} fördelades inte. Fördelade {index}, totalt {len(template_paths)}."
            )

        totals_by_group[group_key] = {
            "label": group_config["label"],
            "input_count": expected_input_count,
            "turn_distribution": dict(group_counter),
        }

    report_payload = {
        "processed_template_count": processed_template_count,
        "groups": totals_by_group,
        "totals_by_turn": dict(sorted(totals_by_turn.items())),
    }
    write_json(outdir / "stage4_distribution_report.json", report_payload)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(stage3_dir),
        "config_path": str(config_path),
        "output_directory": str(outdir),
        "processed_template_count": processed_template_count,
        "totals_by_turn": dict(sorted(totals_by_turn.items())),
    }
    write_json(outdir / "stage4_metadata.json", metadata_payload)

    totals_text = ", ".join(
        f"{turn_count}={totals_by_turn[turn_count]}"
        for turn_count in config["turn_order"]
    )
    print(
        f"Stage 4 complete. Processed {processed_template_count} templates. "
        f"Turn distribution: {totals_text}."
    )


if __name__ == "__main__":
    main()
