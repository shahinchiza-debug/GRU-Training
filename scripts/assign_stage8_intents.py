import argparse
import hashlib
import json
import random
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_STAGE7_DIR = PROJECT_ROOT / "stage7_output" / "valid_templates"
DEFAULT_STAGE8_DIR = PROJECT_ROOT / "stage8_output"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "input" / "stage8_intent_distribution.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_template(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_output_dir(outdir):
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)


def build_rng(namespace, template_id):
    digest = hashlib.sha256(f"{namespace}:{template_id}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def parse_deviation_type(raw_state):
    if not raw_state:
        return None
    return str(raw_state).split("@", 1)[0]


def component_turn_count(component_key, template, config):
    source_key = config["turn_source_by_component"][component_key]
    return int(template["stage7"]["final_turn_allocations"].get(source_key, 0))


def build_assignment(component_key, template, config):
    turn_count = component_turn_count(component_key, template, config)
    intent_min = int(config["intent_range"]["min"])
    intent_max = int(config["intent_range"]["max"])

    if component_key.startswith("D_"):
        raw_state = template[component_key]["state"]
        deviation_type = parse_deviation_type(raw_state)
        intent_allowed = deviation_type in config["intent_allowed_deviation_types"]
        skip_turn_count_cap = deviation_type in config["skip_turn_count_cap_deviation_types"]
        return {
            "component_type": "deviation",
            "state": raw_state,
            "deviation_type": deviation_type,
            "turn_count": turn_count,
            "intent_allowed": intent_allowed,
            "skip_turn_count_cap": skip_turn_count_cap,
            "min_intents": intent_min,
            "max_intents": intent_max
        }

    state_id = template[component_key]["state"]
    intent_allowed = state_id in config["intent_allowed_phase_states"]
    skip_turn_count_cap = state_id in config["skip_turn_count_cap_phase_states"]
    return {
        "component_type": "phase",
        "state": state_id,
        "turn_count": turn_count,
        "intent_allowed": intent_allowed,
        "skip_turn_count_cap": skip_turn_count_cap,
        "min_intents": intent_min,
        "max_intents": intent_max
    }


def annotate_invalid_stage8(template, reason_code, reason, assignments):
    annotated = dict(template)
    annotated = apply_component_intent_counts(annotated, assignments)
    annotated["stage8"] = {
        "valid": False,
        "reason_code": reason_code,
        "reason": reason,
        "assignments": assignments
    }
    return annotated


def annotate_valid_stage8(template, config):
    rng = build_rng(config["random_seed_namespace"], template["template_id"])
    assignments = {}
    total_intent_count = 0

    for component_key in config["evaluation_order"]:
        assignment = build_assignment(component_key, template, config)

        if not assignment["intent_allowed"] or assignment["turn_count"] == 0:
            assignment["effective_max"] = 0
            assignment["intent_count"] = 0
            assignments[component_key] = assignment
            continue

        if assignment["skip_turn_count_cap"]:
            effective_max = assignment["max_intents"]
            assignment["rule_mode"] = "skip_turn_count_cap"
        else:
            effective_max = min(assignment["max_intents"], assignment["turn_count"])
            assignment["rule_mode"] = "use_turn_count_cap"

        assignment["effective_max"] = effective_max

        if effective_max < assignment["min_intents"]:
            reason = (
                f"{component_key} ar ogiltig: turn_count={assignment['turn_count']}, "
                f"min_intents={assignment['min_intents']}, effective_max={effective_max}."
            )
            assignments[component_key] = assignment
            return False, annotate_invalid_stage8(
                template=template,
                reason_code="INTENT_RANGE_INVALID_AFTER_TURN_CAP",
                reason=reason,
                assignments=assignments,
            )

        intent_count = rng.randint(assignment["min_intents"], effective_max)
        assignment["intent_count"] = intent_count
        assignments[component_key] = assignment
        total_intent_count += intent_count

    annotated = dict(template)
    annotated = apply_component_intent_counts(annotated, assignments)
    annotated["stage8"] = {
        "valid": True,
        "assignments": assignments,
        "total_intent_count": total_intent_count
    }
    return True, annotated


def apply_component_intent_counts(template, assignments):
    for component_key, assignment in assignments.items():
        if component_key not in template:
            continue

        component_payload = dict(template[component_key])
        component_payload["intent_count"] = assignment["intent_count"]
        template[component_key] = component_payload

    return template


def write_stage8_readme(outdir):
    readme_text = """# Stage 8 Output

Steg 8 tilldelar intent counts efter att turn counts beraknats i steg 7.

Input:

- `stage7_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Output:

- giltiga mallar: `stage8_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- ogiltiga mallar: `stage8_output/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Regeln som ar inbyggd:

- intent-tillatna faser ar `P2.1`, `P2.2`, `P2.3`, `P2.4`, `P4.2`, `P4.3`
- intent-tillaten avvikelse ar `D5`
- varje `P` och `D` i slutmallen far ett direkt `intent_count`-falt
- om staten ar `P2.2`, `P2.3`, `P4.3` eller `D5` hoppas regeln `intent_count <= turn_count` over
- annars galler:
  - om `turn_count = 3` blir intervallet `1-3`
  - om `turn_count >= 4` blir intervallet `1-4`
"""
    (outdir / "README.md").write_text(readme_text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Assign stage-8 intent counts from stage-7 turn allocations."
    )
    parser.add_argument(
        "--indir",
        default=str(DEFAULT_STAGE7_DIR),
        help="Directory containing valid stage-7 output.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to stage8_intent_distribution.json.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_STAGE8_DIR),
        help="Directory for stage-8 output.",
    )
    args = parser.parse_args()

    indir = Path(args.indir)
    config = load_json(args.config)
    outdir = Path(args.outdir)
    valid_dir = outdir / "valid_templates"
    invalid_dir = outdir / "invalid_templates"

    clear_output_dir(outdir)
    write_stage8_readme(outdir)

    valid_count = 0
    invalid_count = 0
    invalid_reason_counts = Counter()
    totals_by_turn = Counter()
    total_intent_count = 0

    for template_path in sorted(indir.rglob("RAW_*.json")):
        template = load_json(template_path)
        relative_path = template_path.relative_to(indir)
        is_valid, annotated = annotate_valid_stage8(template, config)

        target_root = valid_dir if is_valid else invalid_dir
        write_template(target_root / relative_path, annotated)

        if is_valid:
            valid_count += 1
            totals_by_turn[int(template["stage5"]["turn_count"])] += 1
            total_intent_count += annotated["stage8"]["total_intent_count"]
        else:
            invalid_count += 1
            invalid_reason_counts[annotated["stage8"]["reason_code"]] += 1

    report_payload = {
        "processed_template_count": valid_count + invalid_count,
        "valid_template_count": valid_count,
        "invalid_template_count": invalid_count,
        "invalid_reason_counts": dict(sorted(invalid_reason_counts.items())),
        "valid_totals_by_turn": dict(sorted(totals_by_turn.items())),
        "total_intent_count_across_valid_templates": total_intent_count
    }
    write_json(outdir / "stage8_intent_distribution_report.json", report_payload)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(indir),
        "config_path": str(Path(args.config)),
        "output_directory": str(outdir),
        "valid_template_count": valid_count,
        "invalid_template_count": invalid_count
    }
    write_json(outdir / "stage8_metadata.json", metadata_payload)

    print(f"Stage 8 complete. Valid={valid_count}, invalid={invalid_count}.")


if __name__ == "__main__":
    main()
