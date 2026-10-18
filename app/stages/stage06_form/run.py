import argparse
import json
import math
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_STAGE5_DIR = WORKSPACE_ROOT / "data" / "output" / "stage05_language"
DEFAULT_STAGE6_DIR = WORKSPACE_ROOT / "data" / "output" / "stage06_form"
DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "config" / "stage6_form_distribution.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_template(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_config(config):
    profile_order = config["form_profile_order"]
    profile_weights = config["form_profile_weights"]
    deviation_group_order = config["deviation_group_order"]

    for profile_key in profile_order:
        if profile_key not in config["form_profiles"]:
            raise ValueError(f"Unknown form profile in form_profile_order: {profile_key}")
        if profile_key not in profile_weights:
            raise ValueError(f"Unknown form profile in form_profile_weights: {profile_key}")

    if sum(profile_weights.values()) <= 0:
        raise ValueError("form_profile_weights must have a positive total weight.")

    for group_key in deviation_group_order:
        group_config = config["deviation_groups"].get(group_key)
        if not group_config:
            raise ValueError(f"Unknown deviation group in deviation_group_order: {group_key}")

        placeholders = group_config["distribution_placeholders"]
        variable_components = group_config["variable_components"]
        if set(placeholders.keys()) != set(variable_components):
            raise ValueError(
                f"{group_key} must use the same keys in distribution_placeholders and variable_components."
            )


def clear_output_dir(outdir):
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)


def collect_templates(stage5_dir):
    grouped = defaultdict(list)
    total_count = 0

    for template_path in sorted(stage5_dir.rglob("RAW_*.json")):
        template = load_json(template_path)

        stage4 = template.get("stage4", {})
        stage5 = template.get("stage5", {})
        deviation_group = stage4.get("deviation_group")
        turn_count = stage5.get("turn_count", stage4.get("turn_count"))
        language_bucket = stage5.get("language_bucket")

        if not deviation_group:
            raise ValueError(f"{template_path.name} missing stage4.deviation_group")
        if turn_count is None:
            raise ValueError(f"{template_path.name} missing turn_count")
        if not language_bucket:
            raise ValueError(f"{template_path.name} missing stage5.language_bucket")

        grouped[(language_bucket, int(turn_count))].append(
            {
                "path": template_path,
                "payload": template,
                "deviation_group": deviation_group,
                "turn_count": int(turn_count),
                "language_bucket": language_bucket,
            }
        )
        total_count += 1

    return grouped, total_count


def allocate_counts(total_count, weights, ordered_keys, tie_break_offset=0):
    total_weight = sum(weights[key] for key in ordered_keys)
    allocated = {}
    remainders = []
    rotated_keys = ordered_keys[tie_break_offset:] + ordered_keys[:tie_break_offset]
    rotated_priority = {key: index for index, key in enumerate(rotated_keys)}

    for key in ordered_keys:
        raw_value = total_count * weights[key] / total_weight
        floored = math.floor(raw_value)
        allocated[key] = floored
        remainders.append((raw_value - floored, rotated_priority[key], key))

    remaining = total_count - sum(allocated.values())
    remainders.sort(key=lambda item: (-item[0], item[1]))

    for _, _, key in remainders[:remaining]:
        allocated[key] += 1

    return allocated


def build_stage6_annotation(template, form_profile_key, form_profile, group_config):
    turn_count = int(template["stage5"]["turn_count"])
    fixed_phase_turns = dict(form_profile["fixed_phase_turns"])
    fixed_turn_total = sum(fixed_phase_turns.values())
    remaining_turn_budget = turn_count - fixed_turn_total

    if remaining_turn_budget < 0:
        raise ValueError(
            f"{template['template_id']} has turn_count={turn_count} but form profile {form_profile_key} needs at least {fixed_turn_total} turns."
        )

    annotated = dict(template)
    annotated["stage6"] = {
        "form_profile": form_profile_key,
        "form_profile_label": form_profile["label"],
        "form_profile_description": form_profile["description"],
        "fixed_phase_turns": fixed_phase_turns,
        "fixed_turn_total": fixed_turn_total,
        "remaining_turn_budget": remaining_turn_budget,
        "variable_components": list(group_config["variable_components"]),
        "distribution_placeholders": dict(group_config["distribution_placeholders"]),
        "sum_rule": group_config["sum_rule"]
    }
    return annotated


def write_stage6_readme(outdir):
    readme_text = """# Stage 6 Output

Detta steg lagger till formprofilerna `A1-A2`.

Varje mall far:

- en formprofil (`A1`, `A2`)
- fasta turer for `P1`, `P3` och `P5`
- en `remaining_turn_budget`
- en lista med variabla delar som senare kan fordelas med `X/Y/Z/W`

De delar som fortfarande ar variabla i detta steg ar:

- `P2`
- `P4`
- vid `2D`: `D_slot_1` och `D_slot_2`

Mappstrukturen ar:

- `data/output/stage06_form/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Exempel:

- `data/output/stage06_form/vardaglig_svenska/turn_12/A2/RAW_000123.json`
"""
    (outdir / "README.md").write_text(readme_text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Distribute stage-5 templates into A1-A2 form profiles for stage 6."
    )
    parser.add_argument(
        "--indir",
        default=str(DEFAULT_STAGE5_DIR),
        help="Directory containing stage-5 output.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to stage6_form_distribution.json.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_STAGE6_DIR),
        help="Directory for stage-6 output.",
    )
    args = parser.parse_args()

    stage5_dir = Path(args.indir)
    config_path = Path(args.config)
    outdir = Path(args.outdir)

    config = load_json(config_path)
    validate_config(config)
    grouped_templates, processed_template_count = collect_templates(stage5_dir)

    clear_output_dir(outdir)
    write_stage6_readme(outdir)

    totals_by_deviation_group = Counter()
    totals_by_form_profile = Counter()
    totals_by_language = Counter()
    totals_by_turn = Counter()
    report_languages = {}
    tie_break_offset = 0

    for language_bucket, turn_count in sorted(grouped_templates.keys()):
        templates = grouped_templates[(language_bucket, turn_count)]
        allocations = allocate_counts(
            total_count=len(templates),
            weights=config["form_profile_weights"],
            ordered_keys=config["form_profile_order"],
            tie_break_offset=tie_break_offset,
        )

        if len(templates) % len(config["form_profile_order"]) != 0:
            tie_break_offset = (tie_break_offset + 1) % len(config["form_profile_order"])

        report_languages.setdefault(language_bucket, {"turns": {}})
        report_languages[language_bucket]["turns"][str(turn_count)] = {
            "input_count": len(templates),
            "form_profiles": {}
        }

        index = 0
        for form_profile_key in config["form_profile_order"]:
            form_profile = config["form_profiles"][form_profile_key]
            profile_count = allocations[form_profile_key]
            bucket = templates[index:index + profile_count]

            if len(bucket) != profile_count:
                raise ValueError(
                    f"Wrong bucket length for {language_bucket}/turn_{turn_count}/{form_profile_key}. Expected {profile_count}, got {len(bucket)}."
                )

            for entry in bucket:
                deviation_group = entry["deviation_group"]
                group_config = config["deviation_groups"][deviation_group]
                annotated = build_stage6_annotation(
                    template=entry["payload"],
                    form_profile_key=form_profile_key,
                    form_profile=form_profile,
                    group_config=group_config,
                )

                target_dir = (
                    outdir
                    / entry["language_bucket"]
                    / f"turn_{entry['turn_count']}"
                    / form_profile_key
                )
                target_dir.mkdir(parents=True, exist_ok=True)
                write_template(target_dir / entry["path"].name, annotated)

                totals_by_deviation_group[deviation_group] += 1
                totals_by_form_profile[form_profile_key] += 1
                totals_by_language[entry["language_bucket"]] += 1
                totals_by_turn[entry["turn_count"]] += 1

            report_languages[language_bucket]["turns"][str(turn_count)]["form_profiles"][form_profile_key] = profile_count
            index += profile_count

        if index != len(templates):
            raise ValueError(
                f"Not all templates were distributed in {language_bucket}/turn_{turn_count}. Distributed {index}, total {len(templates)}."
            )

    report_payload = {
        "processed_template_count": processed_template_count,
        "distribution_scope": config["distribution_scope"],
        "languages": report_languages,
        "totals_by_deviation_group": {
            group_key: totals_by_deviation_group[group_key]
            for group_key in config["deviation_group_order"]
        },
        "totals_by_form_profile": {
            profile_key: totals_by_form_profile[profile_key]
            for profile_key in config["form_profile_order"]
        },
        "totals_by_language": dict(sorted(totals_by_language.items())),
        "totals_by_turn": dict(sorted(totals_by_turn.items()))
    }
    write_json(outdir / "stage6_form_distribution_report.json", report_payload)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(stage5_dir),
        "config_path": str(config_path),
        "output_directory": str(outdir),
        "processed_template_count": processed_template_count,
        "distribution_scope": config["distribution_scope"],
        "totals_by_deviation_group": {
            group_key: totals_by_deviation_group[group_key]
            for group_key in config["deviation_group_order"]
        },
        "totals_by_form_profile": {
            profile_key: totals_by_form_profile[profile_key]
            for profile_key in config["form_profile_order"]
        },
        "totals_by_language": dict(sorted(totals_by_language.items())),
        "totals_by_turn": dict(sorted(totals_by_turn.items()))
    }
    write_json(outdir / "stage6_metadata.json", metadata_payload)

    totals_text = ", ".join(
        f"{profile_key}={totals_by_form_profile[profile_key]}"
        for profile_key in config["form_profile_order"]
    )
    print(
        f"Stage 6 complete. Processed {processed_template_count} templates. "
        f"Form profiles: {totals_text}."
    )


if __name__ == "__main__":
    main()
