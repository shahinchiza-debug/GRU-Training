import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_STAGE3_DIR = WORKSPACE_ROOT / "data" / "output" / "stage03_split"
DEFAULT_STAGE4_DIR = WORKSPACE_ROOT / "data" / "output" / "stage04_turns"
DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "config" / "stage4_turn_distribution.json"


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
        allocations = group_config["turn_allocations"]
        percent_total = sum(item["percent"] for item in allocations)
        if percent_total != 100:
            raise ValueError(
                f"Fel i config för {group_key}: procent summerar till {percent_total}, inte 100."
            )

        source_dir = stage3_dir / group_key
        if not source_dir.exists():
            raise ValueError(f"Saknar källmapp för {group_key}: {source_dir}")


def allocate_counts(template_count, allocations):
    """Allocate all templates by percentage using deterministic largest remainder."""
    raw_counts = [template_count * item["percent"] / 100 for item in allocations]
    counts = [int(raw_count) for raw_count in raw_counts]
    remaining = template_count - sum(counts)
    ranked_indexes = sorted(
        range(len(allocations)),
        key=lambda index: (-(raw_counts[index] - counts[index]), index),
    )

    for index in ranked_indexes[:remaining]:
        counts[index] += 1

    return counts


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
        allocated_counts = allocate_counts(
            len(template_paths), group_config["turn_allocations"]
        )

        index = 0
        group_counter = Counter()

        for allocation, count in zip(group_config["turn_allocations"], allocated_counts):
            turn_count = allocation["turn_count"]
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
            "input_count": len(template_paths),
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
