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
DEFAULT_STAGE8_DIR = PROJECT_ROOT / "stage8_output" / "valid_templates"
DEFAULT_STAGE9_DIR = PROJECT_ROOT / "stage9_output"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "input" / "stage9_pools.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_output_dir(outdir):
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)


def build_rng(namespace, template_id):
    digest = hashlib.sha256(f"{namespace}:{template_id}".encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def pick_first_name(rng, config):
    names = (
        config["customer_name_pool"]["first_names_swedish"]
        + config["customer_name_pool"]["first_names_international"]
    )
    return rng.choice(names)


def pick_phone_number(rng, config):
    phone_config = config["customer_phone_pool"]
    prefix = rng.choice(phone_config["prefixes"])
    digits = "".join(rng.choice("0123456789") for _ in range(phone_config["subscriber_digit_length"]))
    return f"{prefix}{digits}"


def pick_day(rng, config, exclude=None):
    days = list(config["day_pool"])
    if exclude is not None:
        days = [day for day in days if day != exclude]
    return rng.choice(days)


def pick_exact_time(rng, config):
    hour = rng.choice(config["time_pool"]["exact_time"]["hour"])
    minute = rng.choice(config["time_pool"]["exact_time"]["minute"])
    return f"{hour}:{minute}"


def pick_time_preference(rng, config, exclude=None):
    kinds = ["exact_time", "relative_time", "time_part"]
    while True:
        kind = rng.choice(kinds)
        if kind == "exact_time":
            value = pick_exact_time(rng, config)
        elif kind == "relative_time":
            value = rng.choice(config["time_pool"]["relative_time"])
        else:
            value = rng.choice(config["time_pool"]["time_part"])

        candidate = {"kind": kind, "value": value}
        if exclude is None or candidate != exclude:
            return candidate


def parse_deviation_state(raw_state):
    if not raw_state:
        return None, None
    deviation_type, phase = str(raw_state).split("@", 1)
    return deviation_type, phase


def add_unique_services(available_services, selected_services, count):
    remaining = [service for service in available_services if service not in selected_services]
    if len(remaining) < count:
        return None
    chosen = remaining[:count]
    selected_services.extend(chosen)
    return chosen


def shuffle_available_services(rng, config):
    services = list(config["service_pool"])
    rng.shuffle(services)
    return services


def get_assignment(template, component_key):
    return template["stage8"]["assignments"][component_key]


def derive_d3_intent_count(template, slot_key):
    assignment = get_assignment(template, slot_key)
    intent_count = int(assignment["intent_count"])
    deviation_type, _ = parse_deviation_state(template[slot_key]["state"])
    if deviation_type == "D3" and intent_count == 0:
        return 1
    return intent_count


def build_p2_payload(template, config, available_services, selected_services, booking_context):
    intent_count = int(get_assignment(template, "P2")["intent_count"])
    if intent_count <= 0:
        return {"intent_count": 0, "intents": []}

    chosen_services = add_unique_services(available_services, selected_services, intent_count)
    if chosen_services is None:
        return None

    intents = []
    for index, service in enumerate(chosen_services, start=1):
        intents.append(
            {
                "intent_id": f"P2_INT_{index:02d}",
                "intent_type": "booking",
                "service": service,
                "day": booking_context["day"],
                "time_preference": booking_context["time_preference"],
            }
        )

    return {"intent_count": intent_count, "intents": intents}


def build_p4_payload(template, config, rng, booking_context):
    intent_count = int(get_assignment(template, "P4")["intent_count"])
    if intent_count <= 0:
        return {"intent_count": 0, "corrections": []}

    corrections = []
    for index in range(intent_count):
        target = "day" if index % 2 == 0 else "time_preference"
        if target == "day":
            value = pick_day(rng, config, exclude=booking_context["day"])
        else:
            value = pick_time_preference(rng, config, exclude=booking_context["time_preference"])
        corrections.append(
            {
                "correction_id": f"P4_COR_{index + 1:02d}",
                "target": target,
                "value": value,
            }
        )

    return {"intent_count": intent_count, "corrections": corrections}


def build_d1_payload(reference_service):
    return {
        "reference_service": reference_service,
        "question_type": "service_info",
    }


def build_correction_deviation_payload(deviation_type, rng, config, booking_context):
    correction_total = 1 if deviation_type == "D2" else 2
    corrections = []
    for index in range(correction_total):
        target = "day" if index % 2 == 0 else "time_preference"
        if target == "day":
            value = pick_day(rng, config, exclude=booking_context["day"])
        else:
            value = pick_time_preference(rng, config, exclude=booking_context["time_preference"])
        corrections.append(
            {
                "correction_id": f"{deviation_type}_COR_{index + 1:02d}",
                "target": target,
                "value": value,
            }
        )
    return {"corrections": corrections}


def build_d3_payload(slot_key, template, available_services, selected_services):
    intent_count = derive_d3_intent_count(template, slot_key)
    if intent_count <= 0:
        return {"intent_count": 0, "intents": []}

    chosen_services = add_unique_services(available_services, selected_services, intent_count)
    if chosen_services is None:
        return None

    intents = []
    for index, service in enumerate(chosen_services, start=1):
        intents.append(
            {
                "intent_id": f"{slot_key}_INT_{index:02d}",
                "intent_type": "add_service",
                "service": service,
            }
        )

    return {"intent_count": intent_count, "intents": intents}


def annotate_invalid_stage9(template, reason_code, reason):
    annotated = dict(template)
    annotated["stage9"] = {
        "valid": False,
        "reason_code": reason_code,
        "reason": reason,
    }
    return annotated


def annotate_valid_stage9(template, config):
    rng = build_rng(config["random_seed_namespace"], template["template_id"])
    available_services = shuffle_available_services(rng, config)
    selected_services = []
    booking_context = {
        "day": pick_day(rng, config),
        "time_preference": pick_time_preference(rng, config),
    }
    customer = {
        "first_name": pick_first_name(rng, config),
        "phone": pick_phone_number(rng, config),
    }
    component_payloads = {}

    p2_payload = build_p2_payload(
        template=template,
        config=config,
        available_services=available_services,
        selected_services=selected_services,
        booking_context=booking_context,
    )
    if p2_payload is None:
        return False, annotate_invalid_stage9(
            template,
            "INSUFFICIENT_UNIQUE_SERVICES",
            "P2 kravde fler unika tjanster an vad servicepoolen kunde ge.",
        )
    component_payloads["P2"] = p2_payload

    p4_payload = build_p4_payload(template, config, rng, booking_context)
    component_payloads["P4"] = p4_payload

    for slot_key in ["D_1", "D_2"]:
        raw_state = template[slot_key]["state"]
        if not raw_state:
            continue

        deviation_type, phase = parse_deviation_state(raw_state)
        payload = {
            "deviation_type": deviation_type,
            "host_phase": phase,
        }

        if deviation_type == "D1":
            reference_service = rng.choice(selected_services) if selected_services else None
            payload.update(build_d1_payload(reference_service))
        elif deviation_type == "D3":
            d3_payload = build_d3_payload(
                slot_key=slot_key,
                template=template,
                available_services=available_services,
                selected_services=selected_services,
            )
            if d3_payload is None:
                return False, annotate_invalid_stage9(
                    template,
                    "INSUFFICIENT_UNIQUE_SERVICES",
                    f"{slot_key} av typ D3 kravde fler unika tjanster an vad servicepoolen kunde ge.",
                )
            payload.update(d3_payload)
        elif deviation_type in {"D2", "D4", "D5"}:
            payload.update(build_correction_deviation_payload(deviation_type, rng, config, booking_context))

        component_payloads[slot_key] = payload

    annotated = dict(template)
    annotated["stage9"] = {
        "valid": True,
        "customer": customer,
        "booking_context": booking_context,
        "selected_services": selected_services,
        "rule_snapshot": {
            "service_sampling_mode": config["pool_rules"]["service_sampling_mode"],
            "allow_duplicate_service_within_template": config["pool_rules"]["allow_duplicate_service_within_template"],
        },
        "component_payloads": component_payloads,
    }
    return True, annotated


def write_stage9_readme(outdir):
    readme_text = """# Stage 9 Output

Steg 9 laser giltiga mallar fran steg 8 och fyller dem med poolvard en.

Input:

- `stage8_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Output:

- giltiga mallar: `stage9_output/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- ogiltiga mallar: `stage9_output/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Vad steg 9 gor:

- drar ett slumpmassigt fornamn
- drar ett slumpmassigt telefonnummer
- drar en dag
- drar en tidspreferens av typen `exact_time`, `relative_time` eller `time_part`
- drar tjanster utan dubletter inom samma mall
- fyller `stage9.component_payloads` for relevanta noder

Viktig regel:

- om en tjanst redan har valts i samma mall far den inte valjas igen

Sarskild notering:

- `D3` behandlas som en service-addition i steg 9 och far minst ett nytt tjanstedrag
  aven om tidigare steg inte redan gav den ett intent count.
"""
    (outdir / "README.md").write_text(readme_text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Populate stage-9 pool values from stage-8 templates."
    )
    parser.add_argument(
        "--indir",
        default=str(DEFAULT_STAGE8_DIR),
        help="Directory containing valid stage-8 output.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to stage9_pools.json.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_STAGE9_DIR),
        help="Directory for stage-9 output.",
    )
    args = parser.parse_args()

    indir = Path(args.indir)
    config = load_json(args.config)
    outdir = Path(args.outdir)
    valid_dir = outdir / "valid_templates"
    invalid_dir = outdir / "invalid_templates"

    clear_output_dir(outdir)
    write_stage9_readme(outdir)

    valid_count = 0
    invalid_count = 0
    invalid_reason_counts = Counter()
    totals_by_language = Counter()
    totals_by_turn = Counter()

    for template_path in sorted(indir.rglob("RAW_*.json")):
        template = load_json(template_path)
        relative_path = template_path.relative_to(indir)
        is_valid, annotated = annotate_valid_stage9(template, config)

        target_root = valid_dir if is_valid else invalid_dir
        write_json(target_root / relative_path, annotated)

        if is_valid:
            valid_count += 1
            totals_by_language[template["stage5"]["language_bucket"]] += 1
            totals_by_turn[int(template["stage5"]["turn_count"])] += 1
        else:
            invalid_count += 1
            invalid_reason_counts[annotated["stage9"]["reason_code"]] += 1

    report_payload = {
        "processed_template_count": valid_count + invalid_count,
        "valid_template_count": valid_count,
        "invalid_template_count": invalid_count,
        "invalid_reason_counts": dict(sorted(invalid_reason_counts.items())),
        "valid_totals_by_language": dict(sorted(totals_by_language.items())),
        "valid_totals_by_turn": dict(sorted(totals_by_turn.items())),
    }
    write_json(outdir / "stage9_report.json", report_payload)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(indir),
        "config_path": str(Path(args.config)),
        "output_directory": str(outdir),
        "valid_template_count": valid_count,
        "invalid_template_count": invalid_count,
    }
    write_json(outdir / "stage9_metadata.json", metadata_payload)

    print(f"Stage 9 complete. Valid={valid_count}, invalid={invalid_count}.")


if __name__ == "__main__":
    main()
