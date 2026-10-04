import argparse
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_STAGE4_DIR = WORKSPACE_ROOT / "data" / "output" / "stage04_turns"
DEFAULT_STAGE5_DIR = WORKSPACE_ROOT / "data" / "output" / "stage05_language"
DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "config" / "stage5_language_distribution.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_template(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_previous_outputs(outdir, language_dirs, report_paths):
    for stale_turn_dir in outdir.glob("turn_*"):
        if stale_turn_dir.is_dir():
            shutil.rmtree(stale_turn_dir)

    for turn_dirs in language_dirs.values():
        for turn_dir in turn_dirs.values():
            for existing_file in turn_dir.glob("RAW_*.json"):
                existing_file.unlink()

    for report_path in report_paths:
        if report_path.exists():
            report_path.unlink()


def build_output_dirs(outdir, config):
    language_dirs = {}
    for language_key in config["language_order"]:
        language_base_dir = outdir / language_key
        language_base_dir.mkdir(parents=True, exist_ok=True)
        turn_dirs = {}
        for turn_count in config["turn_order"]:
            turn_dir = language_base_dir / f"turn_{turn_count}"
            turn_dir.mkdir(parents=True, exist_ok=True)
            turn_dirs[turn_count] = turn_dir
        language_dirs[language_key] = turn_dirs
    return language_dirs


def validate_config(config):
    totals_by_language = Counter()

    for turn_count in config["turn_order"]:
        turn_key = str(turn_count)
        allocation = config["turn_allocations"][turn_key]
        expected_input_count = allocation["expected_input_count"]
        allocated = sum(allocation["languages"].values())
        if expected_input_count != allocated:
            raise ValueError(
                f"Fel i config för turn_{turn_count}: expected_input_count={expected_input_count} men språkallokering summerar till {allocated}."
            )

        for language_key, count in allocation["languages"].items():
            totals_by_language[language_key] += count

    for language_key, language_config in config["languages"].items():
        expected_total = language_config["total"]
        actual_total = totals_by_language[language_key]
        if expected_total != actual_total:
            raise ValueError(
                f"Fel i config för {language_key}: total={expected_total} men turn-fördelningen summerar till {actual_total}."
            )


def gather_templates_for_turn(stage4_dir, turn_count):
    template_paths = []
    for group_dir in sorted(stage4_dir.glob("del_*")):
        turn_dir = group_dir / f"turn_{turn_count}"
        if turn_dir.exists():
            template_paths.extend(sorted(turn_dir.glob("RAW_*.json")))
    return template_paths


def annotate_template(template, turn_count, language_key, language_label):
    annotated = dict(template)
    annotated["stage5"] = {
        "turn_count": turn_count,
        "language_bucket": language_key,
        "language_label": language_label,
    }
    return annotated


def main():
    parser = argparse.ArgumentParser(
        description="Distribute stage-4 templates into language-style buckets for stage 5."
    )
    parser.add_argument(
        "--indir",
        default=str(DEFAULT_STAGE4_DIR),
        help="Directory containing stage-4 output.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to stage5_language_distribution.json.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_STAGE5_DIR),
        help="Directory for stage-5 output.",
    )
    args = parser.parse_args()

    stage4_dir = Path(args.indir)
    config_path = Path(args.config)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    config = load_json(config_path)
    validate_config(config)
    language_dirs = build_output_dirs(outdir, config)
    clear_previous_outputs(
        outdir,
        language_dirs,
        [
            outdir / "stage5_language_distribution_report.json",
            outdir / "stage5_metadata.json",
        ],
    )

    totals_by_language = Counter()
    totals_by_turn = Counter()
    processed_template_count = 0
    per_turn_report = {}

    for turn_count in config["turn_order"]:
        turn_key = str(turn_count)
        allocation = config["turn_allocations"][turn_key]
        template_paths = gather_templates_for_turn(stage4_dir, turn_count)
        expected_input_count = allocation["expected_input_count"]

        if len(template_paths) != expected_input_count:
            raise ValueError(
                f"Fel antal mallar för turn_{turn_count}. Förväntat {expected_input_count}, hittade {len(template_paths)}."
            )

        index = 0
        turn_language_counts = {}

        for language_key in config["language_order"]:
            language_count = allocation["languages"][language_key]
            language_label = config["languages"][language_key]["label"]
            language_dir = language_dirs[language_key][turn_count]
            bucket = template_paths[index:index + language_count]

            if len(bucket) != language_count:
                raise ValueError(
                    f"Fel bucket-längd för turn_{turn_count}/{language_key}. Förväntat {language_count}, fick {len(bucket)}."
                )

            for template_path in bucket:
                template = load_json(template_path)
                annotated = annotate_template(
                    template,
                    turn_count=turn_count,
                    language_key=language_key,
                    language_label=language_label,
                )
                write_template(language_dir / template_path.name, annotated)

            index += language_count
            turn_language_counts[language_key] = language_count
            totals_by_language[language_key] += language_count
            totals_by_turn[turn_count] += language_count
            processed_template_count += language_count

        if index != len(template_paths):
            raise ValueError(
                f"Alla mallar i turn_{turn_count} fördelades inte. Fördelade {index}, totalt {len(template_paths)}."
            )

        per_turn_report[turn_key] = {
            "input_count": expected_input_count,
            "languages": turn_language_counts,
        }

    report_payload = {
        "processed_template_count": processed_template_count,
        "turns": per_turn_report,
        "totals_by_turn": dict(sorted(totals_by_turn.items())),
        "totals_by_language": {
            language_key: totals_by_language[language_key]
            for language_key in config["language_order"]
        },
    }
    write_json(outdir / "stage5_language_distribution_report.json", report_payload)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(stage4_dir),
        "config_path": str(config_path),
        "output_directory": str(outdir),
        "processed_template_count": processed_template_count,
        "totals_by_turn": dict(sorted(totals_by_turn.items())),
        "totals_by_language": {
            language_key: totals_by_language[language_key]
            for language_key in config["language_order"]
        },
    }
    write_json(outdir / "stage5_metadata.json", metadata_payload)

    totals_text = ", ".join(
        f"{language_key}={totals_by_language[language_key]}"
        for language_key in config["language_order"]
    )
    print(
        f"Stage 5 complete. Processed {processed_template_count} templates. "
        f"Language distribution: {totals_text}."
    )


if __name__ == "__main__":
    main()
