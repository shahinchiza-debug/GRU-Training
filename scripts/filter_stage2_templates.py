import argparse
import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_STAGE1_DIR = PROJECT_ROOT / "stage1_output" / "raw_templates"
DEFAULT_STAGE2_DIR = PROJECT_ROOT / "stage2_output"
DEFAULT_RULES_PATH = PROJECT_ROOT / "input" / "stage2_rules.json"
PHASE_KEYS = ["P1", "P2", "P3", "P4", "P5"]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_rule_map(items, key_fields):
    rule_map = {}
    for item in items:
        key = tuple(item[field] for field in key_fields)
        rule_map[key] = {
            "code": item["reason_code"],
            "message": item["reason"],
        }
    return rule_map


def parse_deviation_slot(slot_payload, empty_values):
    state = slot_payload.get("state")
    if state in empty_values:
        return {
            "active": False,
            "raw_state": state,
            "type": None,
            "phase": None,
            "malformed": False,
        }

    if not isinstance(state, str) or "@" not in state:
        return {
            "active": True,
            "raw_state": state,
            "type": None,
            "phase": None,
            "malformed": True,
        }

    deviation_type, phase = state.split("@", 1)
    return {
        "active": True,
        "raw_state": state,
        "type": deviation_type,
        "phase": phase,
        "malformed": False,
    }


def build_rule_sets(rules):
    return {
        "known_deviation_types": set(rules.get("known_deviation_types", [])),
        "invalid_p1_p2_pairs": build_rule_map(rules.get("invalid_p1_p2_pairs", []), ["p1", "p2"]),
        "invalid_p3_p4_pairs": build_rule_map(rules.get("invalid_p3_p4_pairs", []), ["p3", "p4"]),
        "invalid_d_type_phase_pairs": build_rule_map(
            rules.get("invalid_d_type_phase_pairs", []),
            ["type", "phase"],
        ),
        "max_deviation_slots": rules["max_deviation_slots"],
        "empty_state_values": [None],
        "two_deviation_policy": rules["two_deviation_policy"],
    }


def dedupe_errors(errors):
    deduped = []
    seen = set()
    for error in errors:
        fingerprint = (error["code"], error["message"])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduped.append(error)
    return deduped


def build_normalized_deviation_signature(active_deviations, compiled_rules):
    states = [item["raw_state"] for item in active_deviations]
    if len(states) == 2 and compiled_rules["two_deviation_policy"]["dedupe_unordered_pairs"]:
        return tuple(sorted(states))
    return tuple(states)


def build_template_signature(annotated_template, compiled_rules):
    phase_signature = tuple(annotated_template[phase]["state"] for phase in PHASE_KEYS)
    deviation_signature = tuple(annotated_template["_validation"]["derived"]["normalized_deviation_signature"])
    if len(deviation_signature) == 2 and not compiled_rules["two_deviation_policy"]["dedupe_unordered_pairs"]:
        return phase_signature + ("||",) + deviation_signature
    return phase_signature + ("||",) + deviation_signature


def validate_template(template, compiled_rules, rules_path):
    p1 = template["P1"]["state"]
    p2 = template["P2"]["state"]
    p3 = template["P3"]["state"]
    p4 = template["P4"]["state"]
    deviation_1 = parse_deviation_slot(template["D_1"], compiled_rules["empty_state_values"])
    deviation_2 = parse_deviation_slot(template["D_2"], compiled_rules["empty_state_values"])
    active_deviations = [item for item in [deviation_1, deviation_2] if item["active"]]

    errors = []

    pair_rule = compiled_rules["invalid_p1_p2_pairs"].get((p1, p2))
    if pair_rule:
        errors.append(pair_rule)

    p3_p4_rule = compiled_rules["invalid_p3_p4_pairs"].get((p3, p4))
    if p3_p4_rule:
        errors.append(p3_p4_rule)

    if len(active_deviations) > compiled_rules["max_deviation_slots"]:
        errors.append(
            {
                "code": "TOO_MANY_DEVIATIONS",
                "message": (
                    f"Mallen har {len(active_deviations)} deviations men max Ã¤r "
                    f"{compiled_rules['max_deviation_slots']}."
                ),
            }
        )

    for slot_name, deviation in [("D_1", deviation_1), ("D_2", deviation_2)]:
        if not deviation["active"]:
            continue

        if deviation["malformed"]:
            errors.append(
                {
                    "code": "MALFORMED_DEVIATION_STATE",
                    "message": (
                        f"{slot_name} har ett ogiltigt state-format: {deviation['raw_state']!r}. "
                        "FÃ¶rvÃ¤ntat format Ã¤r exempelvis D3@P4."
                    ),
                }
            )
            continue

        if deviation["type"] not in compiled_rules["known_deviation_types"]:
            errors.append(
                {
                    "code": "UNKNOWN_DEVIATION_TYPE",
                    "message": f"{slot_name} anvÃ¤nder okÃ¤nd deviation-typ: {deviation['type']}.",
                }
            )
            continue

        invalid_rule = compiled_rules["invalid_d_type_phase_pairs"].get((deviation["type"], deviation["phase"]))
        if invalid_rule:
            errors.append(invalid_rule)

    if len(active_deviations) == 2:
        same_type = deviation_1["type"] == deviation_2["type"]
        same_phase = deviation_1["phase"] == deviation_2["phase"]
        policy = compiled_rules["two_deviation_policy"]

        if same_type and not policy["allow_same_type"]:
            errors.append(
                {
                    "code": "DOUBLE_DEVIATION_SAME_TYPE_NOT_ALLOWED",
                    "message": "TvÃ¥ deviations med samma typ Ã¤r inte tillÃ¥tna enligt stage2_rules.",
                }
            )

        if same_phase and not policy["allow_same_phase"]:
            errors.append(
                {
                    "code": "DOUBLE_DEVIATION_SAME_PHASE_NOT_ALLOWED",
                    "message": "TvÃ¥ deviations i samma fas Ã¤r inte tillÃ¥tna enligt stage2_rules.",
                }
            )

    deduped_errors = dedupe_errors(errors)
    normalized_deviation_signature = build_normalized_deviation_signature(active_deviations, compiled_rules)

    annotated = deepcopy(template)
    annotated["_validation"] = {
        "valid": len(deduped_errors) == 0,
        "rules_path": str(rules_path),
        "reason_codes": [error["code"] for error in deduped_errors],
        "reasons": [error["message"] for error in deduped_errors],
        "derived": {
            "deviation_count": len(active_deviations),
            "active_deviations": [
                {
                    "slot": "D_1" if deviation is deviation_1 else "D_2",
                    "state": deviation["raw_state"],
                    "type": deviation["type"],
                    "phase": deviation["phase"],
                }
                for deviation in active_deviations
            ],
            "normalized_deviation_signature": list(normalized_deviation_signature),
        },
    }
    return annotated


def mark_duplicate_structure(annotated_template):
    code = "DUPLICATE_UNORDERED_DEVIATION_PAIR"
    message = "Mallen Ã¤r en duplikatstruktur dÃ¤r D_1 och D_2 bara skiljer sig i slot-ordning."

    if code not in annotated_template["_validation"]["reason_codes"]:
        annotated_template["_validation"]["reason_codes"].append(code)
        annotated_template["_validation"]["reasons"].append(message)

    annotated_template["_validation"]["valid"] = False
    return annotated_template


def clear_previous_outputs(valid_dir, invalid_dir, outdir):
    for directory in [valid_dir, invalid_dir]:
        for existing_file in directory.glob("RAW_*.json"):
            existing_file.unlink()

    for report_file in [outdir / "stage2_filter_report.json", outdir / "stage2_metadata.json"]:
        if report_file.exists():
            report_file.unlink()


def main():
    parser = argparse.ArgumentParser(description="Filter stage-1 raw templates into valid and invalid step-2 outputs.")
    parser.add_argument("--indir", default=str(DEFAULT_STAGE1_DIR), help="Directory containing RAW_*.json templates from stage 1.")
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH), help="Path to stage2_rules.json.")
    parser.add_argument("--outdir", default=str(DEFAULT_STAGE2_DIR), help="Directory for stage-2 output.")
    parser.add_argument("--limit", type=int, help="Optional debug limit. If omitted, all stage-1 templates are processed.")
    args = parser.parse_args()

    indir = Path(args.indir)
    rules_path = Path(args.rules)
    outdir = Path(args.outdir)
    valid_dir = outdir / "valid_templates"
    invalid_dir = outdir / "invalid_templates"

    outdir.mkdir(parents=True, exist_ok=True)
    valid_dir.mkdir(parents=True, exist_ok=True)
    invalid_dir.mkdir(parents=True, exist_ok=True)

    rules = load_json(rules_path)
    compiled_rules = build_rule_sets(rules)
    clear_previous_outputs(valid_dir, invalid_dir, outdir)

    template_paths = sorted(indir.glob("RAW_*.json"))
    if args.limit is not None:
        template_paths = template_paths[: args.limit]

    if not template_paths:
        raise ValueError(f"Inga RAW_*.json-filer hittades i {indir}")

    valid_count = 0
    invalid_count = 0
    duplicate_structure_count = 0
    invalid_reason_counter = Counter()
    seen_signatures = set()

    for template_path in template_paths:
        template = load_json(template_path)
        annotated = validate_template(template, compiled_rules, rules_path)

        if annotated["_validation"]["valid"]:
            signature = build_template_signature(annotated, compiled_rules)
            if signature in seen_signatures:
                annotated = mark_duplicate_structure(annotated)
                duplicate_structure_count += 1
            else:
                seen_signatures.add(signature)

        if annotated["_validation"]["valid"]:
            valid_count += 1
            write_json(valid_dir / template_path.name, annotated)
        else:
            invalid_count += 1
            for code in annotated["_validation"]["reason_codes"]:
                invalid_reason_counter[code] += 1
            write_json(invalid_dir / template_path.name, annotated)

    report_payload = {
        "processed_template_count": len(template_paths),
        "valid_template_count": valid_count,
        "invalid_template_count": invalid_count,
        "duplicate_structure_count": duplicate_structure_count,
        "invalid_reason_counts": dict(sorted(invalid_reason_counter.items())),
        "two_deviation_policy": compiled_rules["two_deviation_policy"],
    }
    write_json(outdir / "stage2_filter_report.json", report_payload)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(indir),
        "rules_path": str(rules_path),
        "output_directory": str(outdir),
        "processed_template_count": len(template_paths),
        "limit_used": args.limit,
        "valid_template_count": valid_count,
        "invalid_template_count": invalid_count,
        "duplicate_structure_count": duplicate_structure_count,
        "two_deviation_policy": compiled_rules["two_deviation_policy"],
    }
    write_json(outdir / "stage2_metadata.json", metadata_payload)

    print(
        f"Stage 2 complete. Processed {len(template_paths)} templates: "
        f"{valid_count} valid, {invalid_count} invalid."
    )


if __name__ == "__main__":
    main()

