import argparse
import hashlib
import json
import random
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_STAGE7_DIR = WORKSPACE_ROOT / "data" / "output" / "stage07_dirichlet" / "valid_templates"
DEFAULT_STAGE8_DIR = WORKSPACE_ROOT / "data" / "output" / "stage08_intents"
DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "config" / "stage8_intent_distribution.json"


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

    if component_key.startswith("D_"):
        raw_state = template[component_key]["state"]
        deviation_type = parse_deviation_type(raw_state)
        return {
            "component_type": "deviation",
            "state": raw_state,
            "deviation_type": deviation_type,
            "turn_count": turn_count,
            "intent_count": 0,
        }

    state_id = template[component_key]["state"]
    return {
        "component_type": "phase",
        "state": state_id,
        "turn_count": turn_count,
        "intent_count": 0,
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


def allowed_counts(options, assignment, config):
    limits = config["count_limits"]
    state = assignment.get("deviation_type") or assignment["state"]
    maximum = limits["max_count"]
    if state not in limits["skip_turn_cap_states"]:
        maximum = min(maximum, assignment["turn_count"])
    return [count for count in options if 0 <= count <= maximum]


def flow_components(template):
    """Return components in the same order that later stages execute them."""
    deviations_by_phase = {phase: [] for phase in ("P1", "P2", "P3", "P4", "P5")}
    for slot in ("D_1", "D_2"):
        raw_state = template[slot]["state"]
        if raw_state:
            _, phase = raw_state.split("@", 1)
            deviations_by_phase[phase].append(slot)

    result = []
    for phase in ("P1", "P2", "P3", "P4"):
        result.append(phase)
        result.extend(deviations_by_phase[phase])
    result.extend(deviations_by_phase["P5"])
    result.append("P5")
    return result


def assign_target_counts(template, assignments, config, rng):
    """Choose counts only from IDs that exist before each correction block."""
    active_target_count = 0

    for component_key in flow_components(template):
        assignment = assignments[component_key]
        state = assignment.get("state")
        deviation_type = assignment.get("deviation_type")

        if component_key == "P2":
            active_target_count += assignment["intent_count"]
            continue
        if component_key == "P3":
            active_target_count += assignment["intent_count"]
            continue
        if deviation_type == "D3":
            active_target_count += assignment["intent_count"]
            continue

        if component_key == "P4":
            configured = config["target_count_by_phase_state"][state]
        elif deviation_type in {"D2", "D5"}:
            configured = config["target_count_by_deviation_type"][deviation_type]
        else:
            continue

        options = allowed_counts(configured, assignment, config)
        options = [count for count in options if count <= active_target_count]
        if not options:
            return False, component_key, active_target_count

        assignment["available_target_count"] = active_target_count
        assignment["target_count"] = rng.choice(options)
        assignment["intent_count"] = 0

    return True, None, None


def annotate_valid_stage8(template, config):
    rng = build_rng(config["random_seed_namespace"], template["template_id"])
    assignments = {
        component_key: build_assignment(component_key, template, config)
        for component_key in config["evaluation_order"]
    }

    for state, minimum_turns in config.get("minimum_turns_by_phase_state", {}).items():
        if template["P2"]["state"] == state and assignments["P2"]["turn_count"] < minimum_turns:
            return False, annotate_invalid_stage8(
                template,
                "INSUFFICIENT_STATE_TURNS",
                f"{state} requires at least {minimum_turns} customer turns.",
                assignments,
            )

    service_rules = config["service_plan"]
    d3_slots = [slot for slot in ("D_1", "D_2") if parse_deviation_type(template[slot]["state"]) == "D3"]
    max_p2 = service_rules["max_total_services"] - len(d3_slots) * service_rules["d3_service_count"]
    p2_options = [count for count in service_rules["p2_service_counts_by_state"][template["P2"]["state"]] if count <= max_p2]
    if not p2_options:
        raise ValueError("P2 och D3 ryms inte inom tjänsttaket.")
    # One booking ID plus the service IDs must fit the count limit.
    allowed_p2_counts = allowed_counts([1 + count for count in p2_options], assignments["P2"], config)
    p2_options = [count for count in p2_options if 1 + count in allowed_p2_counts]
    if not p2_options:
        return False, annotate_invalid_stage8(
            template, "NO_VALID_COUNT", "P2: state counts do not fit the count/turn limit.", assignments
        )
    service_plan = {
        "max_total_services": service_rules["max_total_services"],
        "P2": {"service_count": rng.choice(p2_options)},
        "D_1": {"service_count": service_rules["d3_service_count"] if "D_1" in d3_slots else 0},
        "D_2": {"service_count": service_rules["d3_service_count"] if "D_2" in d3_slots else 0}
    }

    # Counts reflect created objects after filtering by state and turn limits.
    # P2 always creates BOOK_001 plus the state's required services.
    assignments["P2"]["intent_count"] = 1 + service_plan["P2"]["service_count"]
    assignments["P2"]["rule_mode"] = "derived_from_booking_and_services"
    assignments["P3"]["intent_count"] = 1
    assignments["P3"]["rule_mode"] = "fixed_auth_creation"
    for slot in d3_slots:
        assignments[slot]["intent_count"] = service_rules["d3_service_count"]
        assignments[slot]["rule_mode"] = "fixed_service_addition"

    # Corrections do not create intents. Their count must fit IDs created earlier in flow.
    target_counts_fit, failed_component, available_target_count = assign_target_counts(
        template, assignments, config, rng
    )
    if not target_counts_fit:
        return False, annotate_invalid_stage8(
            template,
            "INSUFFICIENT_ACTIVE_TARGETS",
            f"{failed_component} requires more targets than the {available_target_count} active IDs in flow.",
            assignments,
        )

    for component_key, assignment in assignments.items():
        for field in ("intent_count", "target_count"):
            count = assignment.get(field, 0)
            if count and not allowed_counts([count], assignment, config):
                return False, annotate_invalid_stage8(
                    template, "NO_VALID_COUNT", f"{component_key}: {field} exceeds count/turn limit.", assignments
                )

    total_intent_count = sum(item.get("intent_count", 0) for item in assignments.values())

    annotated = dict(template)
    annotated = apply_component_intent_counts(annotated, assignments)
    annotated["stage8"] = {
        "valid": True,
        "assignments": assignments,
        "total_intent_count": total_intent_count,
        "service_plan": service_plan
    }
    return True, annotated


def apply_component_intent_counts(template, assignments):
    for component_key, assignment in assignments.items():
        if component_key not in template:
            continue

        component_payload = dict(template[component_key])
        component_payload.pop("intent_count", None)
        component_payload.pop("target_count", None)
        if assignment.get("intent_count", 0) > 0:
            component_payload["intent_count"] = assignment["intent_count"]
        if "target_count" in assignment:
            component_payload["target_count"] = assignment["target_count"]
        template[component_key] = component_payload

    return template


def write_stage8_readme(outdir):
    readme_text = """# Stage 8 Output

Steg 8 tilldelar intent counts efter att turn counts beraknats i steg 7.

Input:

- `data/output/stage07_dirichlet/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Output:

- giltiga mallar: `data/output/stage08_intents/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- ogiltiga mallar: `data/output/stage08_intents/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Regler som ar inbyggda:

- `intent_count` ar antalet nya `intent_id` som komponenten skapar.
- P2 raknas som `BOOK_001` plus antal valda tjanster.
- P2.1 skapar bara `BOOK_001` och far `intent_count` 1.
- P2.2, P2.3 och P2.4 skapar `BOOK_001` plus 1-3 tjanster och far `intent_count` 2-4.
- P3 skapar alltid `AUTH_001` och far `intent_count` 1.
- D3 skapar alltid en ny tjanst och far `intent_count` 1.
- P4, D2 och D5 skapar inga nya intent utan anvander `target_count`.
- `target_count` valjs bara bland de ID:n som redan ar aktiva precis fore blocket i flow.
- Steg 9 far aldrig sanka en target_count; den ska redan vara mojlig i steg 8.
- Counts begransas till max 4 och normalt till antalet kundturer.
- Endast P2.2 undantar intent_count fran turgransen. P2.3 och P2.4 foljer intent_count <= customer_turns; P4.3/D5 undantar target_count.
- State-regler galler samtidigt. Saknas giltigt count sorteras mallen som ogiltig.
- Bokningen ingar i P2:s count, sa max 4 intents betyder hogst 3 tjanster i P2.
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
