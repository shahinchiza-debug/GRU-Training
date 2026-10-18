import argparse
import hashlib
import json
import random
import shutil
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.shared.service_rules import is_compatible_service


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parents[2]
DEFAULT_STAGE8_DIR = WORKSPACE_ROOT / "data" / "output" / "stage08_intents" / "valid_templates"
DEFAULT_STAGE9_DIR = WORKSPACE_ROOT / "data" / "output" / "stage09_pools"
DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "config" / "stage9_pools.json"
PHASE_ORDER = {phase: index for index, phase in enumerate(("P1", "P2", "P3", "P4", "P5"))}


class SessionState:
    """Tracks objects that are available at the current point in one template flow."""

    def __init__(self):
        self.booking_active = False
        self.auth_active = False
        self.active_services = {}
        self.next_service_number = 1

    def create_booking(self):
        self.booking_active = True

    def create_auth(self):
        self.auth_active = True

    def add_services(self, services):
        service_ids = []
        for service in services:
            service_id = f"SVC_{self.next_service_number:03d}"
            self.active_services[service_id] = service
            self.next_service_number += 1
            service_ids.append(service_id)
        return service_ids

    def active_target_ids(self):
        target_ids = []
        if self.booking_active:
            target_ids.append("BOOK_001")
        if self.auth_active:
            target_ids.append("AUTH_001")
        return target_ids + list(self.active_services)

    def apply_corrections(self, corrections):
        for correction in corrections:
            if correction["mlp1"] == "Tjänster" and correction["mlp2"] == "byta ut":
                self.active_services[correction["target_id"]] = correction["parameters"]["service"]


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


def pick_staff(rng, config, exclude=None):
    staff_pool = list(config["staff_pool"])
    if exclude is not None:
        staff_pool = [staff for staff in staff_pool if staff != exclude]
    return rng.choice(staff_pool)


def pick_exact_time(rng, config):
    hour = rng.choice(config["time_pool"]["exact_time"]["hour"])
    minute = rng.choice(config["time_pool"]["exact_time"]["minute"])
    return f"{hour}:{minute}"


def pick_booking_time(rng, config, exclude=None):
    """Bookings always store an exact time; other time pools are for AI rendering later."""
    while True:
        candidate = {"kind": "exact_time", "value": pick_exact_time(rng, config)}
        if exclude is None or candidate != exclude:
            return candidate


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


def normalize_service_name(value):
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_value.lower().strip()


def derive_booking_duration_minutes(selected_services, config):
    duration_rules = config["booking_duration_rules"]
    allowed_durations = set(duration_rules["allowed_duration_minutes"])
    override_minutes = {
        normalize_service_name(service): minutes
        for service, minutes in duration_rules["single_service_override_minutes"].items()
    }

    if len(selected_services) >= 2:
        candidate = duration_rules["multi_service_minutes"]
    elif len(selected_services) == 1:
        service_key = normalize_service_name(selected_services[0])
        candidate = override_minutes.get(
            service_key,
            duration_rules["single_service_default_minutes"],
        )
    else:
        candidate = duration_rules["single_service_default_minutes"]

    if candidate not in allowed_durations:
        raise ValueError(f"Unsupported booking duration: {candidate}")
    return candidate


def parse_deviation_state(raw_state):
    if not raw_state:
        return None, None
    deviation_type, phase = str(raw_state).split("@", 1)
    return deviation_type, phase


def ordered_deviation_slots(template):
    deviations = []
    for slot_index, slot_key in enumerate(("D_1", "D_2")):
        raw_state = template[slot_key]["state"]
        if not raw_state:
            continue
        deviation_type, phase = parse_deviation_state(raw_state)
        deviations.append((PHASE_ORDER[phase], slot_index, slot_key, deviation_type, phase))
    return sorted(deviations)


def add_unique_services(available_services, selected_services, count, config):
    if count == 0:
        return []

    chosen = []
    for service in available_services:
        active_services = selected_services + chosen
        if is_compatible_service(service, active_services, config):
            chosen.append(service)
            if len(chosen) == count:
                selected_services.extend(chosen)
                return chosen
    return None


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


def build_p2_payload(template, config, available_services, selected_services, booking_context, session):
    service_count = int(template["stage8"]["service_plan"]["P2"]["service_count"])

    chosen_services = add_unique_services(available_services, selected_services, service_count, config)
    if chosen_services is None:
        return None

    session.create_booking()
    service_ids = session.add_services(chosen_services)
    intents = []
    for service_id, service in zip(service_ids, chosen_services):
        intents.append(
            {
                "intent_id": service_id,
                "intent_type": "booking",
                "service": service,
                "day": booking_context["day"],
                "time_preference": booking_context["time_preference"],
            }
        )

    return {"service_count": service_count, "intents": intents}


def build_corrections(prefix, target_count, target_ids, rng, config, booking_context, active_services=None):
    # Count objects, not the number of fields changed within each object.
    if target_count < 0 or (prefix == "D2" and target_count != 1) or (prefix == "D5" and target_count < 2):
        raise ValueError(f"{prefix}: invalid unique target_count {target_count}")
    available_target_ids = list(dict.fromkeys(target_ids))
    if target_count > len(available_target_ids):
        return None

    # Reserve replacements immediately so two service changes in one block
    # cannot select the same final service.
    working_services = dict(active_services or {})
    corrections = []
    for index in range(target_count):
        target_id = rng.choice(available_target_ids)
        available_target_ids.remove(target_id)
        if target_id == "BOOK_001":
            mlp1 = "Booking"
            mlp2 = rng.choice(("ändra", "omboka"))
            if mlp2 == "ändra":
                field = "staff"
                value = pick_staff(rng, config, exclude=booking_context["staff"])
            else:
                field = "day" if index % 2 == 0 else "time_preference"
                value = (
                    pick_day(rng, config, exclude=booking_context["day"])
                    if field == "day"
                    else pick_booking_time(
                        rng, config, exclude=booking_context["time_preference"]
                    )
                )
        elif target_id == "AUTH_001":
            field, value, mlp1, mlp2 = "phone", pick_phone_number(rng, config), "Auth", "ändra"
        else:
            current_service = working_services.get(target_id)
            if current_service is None:
                return None
            other_active_services = {
                service_id: service
                for service_id, service in working_services.items()
                if service_id != target_id
            }
            candidates = [
                service for service in config["service_pool"]
                if service != current_service
                and is_compatible_service(
                    service, list(other_active_services.values()), config
                )
            ]
            if not candidates:
                return None
            field, value, mlp1, mlp2 = "service", rng.choice(candidates), "Tjänster", "byta ut"
            working_services[target_id] = value
        item = {"correction_id": f"{prefix}_COR_{index + 1:02d}", "target_id": target_id, "mlp1": mlp1, "mlp2": mlp2}
        if value is not None:
            item["parameters"] = {field: value}
        corrections.append(item)
    return corrections


def resolve_target_count(component, requested_count, target_ids):
    """Accept the stage-8 count only when the exact capacity exists."""
    minimum = 2 if component in {"P4.3", "D5"} else 1
    available_count = len(set(target_ids))
    if requested_count < minimum or requested_count > available_count:
        return None
    return requested_count


def build_p4_payload(template, config, rng, booking_context, session):
    requested_target_count = int(get_assignment(template, "P4")["target_count"])
    if requested_target_count <= 0:
        return {"target_count": 0, "corrections": []}

    target_count = resolve_target_count(
        template["P4"]["state"], requested_target_count, session.active_target_ids()
    )
    if target_count is None:
        return None
    corrections = build_corrections(
        "P4", target_count, session.active_target_ids(), rng, config, booking_context,
        session.active_services,
    )
    if corrections is None:
        return None
    return {"target_count": target_count, "corrections": corrections}


def build_d1_payload(session, rng, config):
    """Creates a general FAQ or one that references an active object in the flow."""
    faq_rules = config["d1_faq_rules"]
    references = []

    if session.booking_active and "booking" in faq_rules["reference_pools"]:
        references.append(("booking", "BOOK_001"))
    if session.auth_active and "auth" in faq_rules["reference_pools"]:
        references.append(("auth", "AUTH_001"))
    if "service" in faq_rules["reference_pools"]:
        references.extend(("service", service_id) for service_id in session.active_services)

    if references and rng.choice([True, False]):
        pool, target_id = rng.choice(references)
        return {"pool": pool, "reference_id": target_id}
    return {"pool": faq_rules["general_pool"]}


def build_correction_deviation_payload(deviation_type, target_count, target_ids, rng, config, booking_context, active_services):
    corrections = build_corrections(
        deviation_type, target_count, target_ids, rng, config, booking_context, active_services
    )
    if corrections is None:
        return None
    return {"corrections": corrections}


def build_d3_payload(slot_key, template, available_services, selected_services, config, session):
    service_count = int(template["stage8"]["service_plan"][slot_key]["service_count"])

    chosen_services = add_unique_services(available_services, selected_services, service_count, config)
    if chosen_services is None:
        return None

    service_ids = session.add_services(chosen_services)
    intents = []
    for service_id, service in zip(service_ids, chosen_services):
        intents.append(
            {
                "intent_id": service_id,
                "intent_type": "add_service",
                "service": service,
            }
        )

    return {"service_count": service_count, "intents": intents}


def attach_duration_to_booking_payloads(component_payloads, duration_minutes):
    p2_payload = component_payloads.get("P2")
    if not p2_payload:
        return

    for intent in p2_payload.get("intents", []):
        intent["duration_minutes"] = duration_minutes


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
    session = SessionState()
    booking_context = {
        "day": pick_day(rng, config),
        "time_preference": pick_booking_time(rng, config),
        "staff": pick_staff(rng, config),
    }
    component_payloads = {}

    deviations_by_phase = {phase: [] for phase in PHASE_ORDER}
    for _, _, slot_key, deviation_type, phase in ordered_deviation_slots(template):
        deviations_by_phase[phase].append((slot_key, deviation_type))

    def build_deviation(slot_key, deviation_type, host_phase):
        payload = {"deviation_type": deviation_type, "host_phase": host_phase}

        if deviation_type == "D1":
            payload.update(build_d1_payload(session, rng, config))
        elif deviation_type == "D3":
            d3_payload = build_d3_payload(
                slot_key, template, available_services, selected_services, config, session
            )
            if d3_payload is None:
                return None, "INSUFFICIENT_UNIQUE_SERVICES"
            payload.update(d3_payload)
        elif deviation_type in {"D2", "D5"}:
            requested_target_count = int(get_assignment(template, slot_key).get("target_count", 0))
            if (deviation_type == "D2" and requested_target_count != 1) or (deviation_type == "D5" and requested_target_count < 2):
                return None, "INVALID_TARGET_COUNT"
            target_count = resolve_target_count(
                deviation_type, requested_target_count, session.active_target_ids()
            )
            if target_count is None:
                return None, "INSUFFICIENT_UNIQUE_TARGETS"
            corrections = build_correction_deviation_payload(
                deviation_type, target_count, session.active_target_ids(), rng, config, booking_context,
                session.active_services,
            )
            if corrections is None:
                return None, "INSUFFICIENT_UNIQUE_TARGETS"
            payload["target_count"] = target_count
            payload.update(corrections)
            session.apply_corrections(corrections["corrections"])
            selected_services[:] = list(session.active_services.values())

        return payload, None

    for phase in ("P1", "P2", "P3", "P4"):
        if phase == "P2":
            p2_payload = build_p2_payload(
                template, config, available_services, selected_services, booking_context, session
            )
            if p2_payload is None:
                return False, annotate_invalid_stage9(
                    template,
                    "INSUFFICIENT_UNIQUE_SERVICES",
                    "P2 kravde fler giltiga kompatibla tjanster an vad servicepoolen kunde ge.",
                )
            component_payloads["P2"] = p2_payload
        elif phase == "P3":
            component_payloads["P3"] = {
                "intent_id": "AUTH_001",
                "mlp1": "Auth",
                "mlp2": "skapa",
                "parameters": {
                    "name": pick_first_name(rng, config),
                    "phone": pick_phone_number(rng, config),
                },
            }
            session.create_auth()
        elif phase == "P4":
            p4_payload = build_p4_payload(template, config, rng, booking_context, session)
            if p4_payload is None:
                return False, annotate_invalid_stage9(
                    template,
                    "INSUFFICIENT_UNIQUE_TARGETS",
                    "P4 kravde fler unika targets an vad som ar aktiva vid P4.",
                )
            component_payloads["P4"] = p4_payload
            session.apply_corrections(p4_payload["corrections"])
            selected_services[:] = list(session.active_services.values())

        for slot_key, deviation_type in deviations_by_phase[phase]:
            payload, reason_code = build_deviation(slot_key, deviation_type, phase)
            if reason_code:
                return False, annotate_invalid_stage9(
                    template,
                    reason_code,
                    f"{slot_key} av typ {deviation_type} saknade giltiga objekt i flow-ordning.",
                )
            component_payloads[slot_key] = payload

    # A P5 deviation happens before the closing node, matching the final flow layout.
    for slot_key, deviation_type in deviations_by_phase["P5"]:
        payload, reason_code = build_deviation(slot_key, deviation_type, "P5")
        if reason_code:
            return False, annotate_invalid_stage9(
                template,
                reason_code,
                f"{slot_key} av typ {deviation_type} saknade giltiga objekt i flow-ordning.",
            )
        component_payloads[slot_key] = payload

    active_services = list(session.active_services.values())
    booking_context["duration_minutes"] = derive_booking_duration_minutes(active_services, config)
    if len(selected_services) > template["stage8"]["service_plan"]["max_total_services"]:
        raise ValueError("Tjänsttaket överskreds trots service_plan.")
    attach_duration_to_booking_payloads(component_payloads, booking_context["duration_minutes"])

    annotated = dict(template)
    annotated["stage9"] = {
        "valid": True,
        "booking_context": booking_context,
        "selected_services": selected_services,
        "service_plan": template["stage8"]["service_plan"],
        "rule_snapshot": {
            "service_sampling_mode": config["pool_rules"]["service_sampling_mode"],
            "allow_duplicate_service_within_template": config["pool_rules"]["allow_duplicate_service_within_template"],
            "exclusive_service_groups": config.get("exclusive_service_groups", []),
            "incompatible_service_pairs": config.get("incompatible_service_pairs", []),
            "allowed_duration_minutes": config["booking_duration_rules"]["allowed_duration_minutes"],
        },
        "component_payloads": component_payloads,
    }
    return True, annotated


def write_stage9_readme(outdir):
    readme_text = """# Stage 9 Output

Steg 9 laser giltiga mallar fran steg 8 och fyller dem med poolvard en.

Input:

- `data/output/stage08_intents/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Output:

- giltiga mallar: `data/output/stage09_pools/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- ogiltiga mallar: `data/output/stage09_pools/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Vad steg 9 gor:

- drar ett slumpmassigt fornamn
- drar ett slumpmassigt telefonnummer
- drar en dag
- drar alltid en exakt bokningstid från `exact_time`
- behåller `relative_time` och `time_part` i poolen för ett senare AI-renderingssteg
- raknar ut bokningstid som `30` eller `60` minuter beroende pa tjanst och tillaegg
- drar tjanster utan dubletter inom samma mall
- filtrerar bort tjanster som bryter mot kompatibilitetsreglerna
- fyller `stage9.component_payloads` for relevanta noder

Viktig regel:

- om en tjanst redan har valts i samma mall far den inte valjas igen
- endast en tjanst i gruppen `klippning` far valjas
- `damklippning` och `skaggtrimning` far inte kombineras
- exakta tider dras bara pa `00` eller `30`

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
