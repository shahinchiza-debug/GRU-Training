import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.shared.service_rules import validate_active_services


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / "data" / "output" / "stage09_pools" / "valid_templates"
DEFAULT_OUTPUT = ROOT / "data" / "output" / "stage10_hierarchy"
DEFAULT_CONFIG = ROOT / "config" / "stage10_hierarchy.json"
DEFAULT_POOL_CONFIG = ROOT / "config" / "stage9_pools.json"
TARGET_MLP1_BY_PREFIX = {
    "BOOK_": "Booking",
    "SVC_": "Tjänster",
    "AUTH_": "Auth",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def load_config(path=DEFAULT_CONFIG):
    """Load the one rule source that governs the stage-10 hierarchy."""
    config = load_json(path)
    required = {
        "p2_service_count_by_state",
        "target_count_by_phase_state",
        "target_count_by_deviation_type",
        "intent_creators",
        "target_actions",
        "d1_faq_rules",
        "state_instructions",
    }
    missing = required - set(config)
    if missing:
        raise ValueError(f"Stage 10 config saknar: {', '.join(sorted(missing))}")
    return config


def active_deviations(source):
    result = []
    for slot in ("D_1", "D_2"):
        state = source[slot]["state"]
        if state:
            kind, phase = state.split("@", 1)
            result.append((slot, kind, phase))
    return result


def deviation_node_ids(deviations):
    """Give repeated deviation types distinct node IDs within one template."""
    type_counts = Counter(kind for _, kind, _ in deviations)
    type_indices = Counter()
    node_ids = {}
    for slot, kind, _ in deviations:
        type_indices[kind] += 1
        node_ids[slot] = kind if type_counts[kind] == 1 else f"{kind}_{type_indices[kind]}"
    return node_ids


def expected_mlp1_for_target(target_id):
    for prefix, mlp1 in TARGET_MLP1_BY_PREFIX.items():
        if target_id.startswith(prefix):
            return mlp1
    return None


def phase_node(source, phase, config):
    state = source[phase]["state"]
    return {
        "type": "phase",
        "state": state,
        "customer_turns": source["stage7"]["final_turn_allocations"][phase],
        "instruction": config["state_instructions"][state],
    }


def p2_intents(stage9):
    payload = stage9["component_payloads"].get("P2")
    if not payload:
        return []

    booking = stage9["booking_context"]
    time_preference = booking["time_preference"]
    time_value = time_preference["value"] if isinstance(time_preference, dict) else time_preference
    intents = [{
        "intent_id": "BOOK_001",
        "mlp1": "Booking",
        "mlp2": "boka",
        "parameters": {
            "day": booking["day"],
            "time": time_value,
            "staff": booking["staff"],
        },
    }]
    for item in payload["intents"]:
        intents.append({
            "intent_id": item["intent_id"],
            "mlp1": "Tjänster",
            "mlp2": "lägga till",
            "parameters": {"service": item["service"]},
        })
    return intents


def clean_targets(corrections):
    return [
        {
            key: value
            for key, value in correction.items()
            if key != "correction_id"
        }
        for correction in corrections
    ]


def validate_hierarchy(template, config=None, pool_config=None):
    """Validate object references in flow order, independent of field changes."""
    config = config or load_config()
    pool_config = pool_config or load_json(DEFAULT_POOL_CONFIG)
    allowed_creators = {key: set(value) for key, value in config["intent_creators"].items()}
    allowed_actions = {key: set(value) for key, value in config["target_actions"].items()}
    d1_rules = config["d1_faq_rules"]
    reference_prefixes = {"booking": "BOOK_", "service": "SVC_", "auth": "AUTH_"}
    active = set()
    active_services = {}
    for node_id in template["flow"]:
        node = template["nodes"][node_id]
        state = node["state"]
        intents = node.get("intents", [])
        if "intent_count" in node and node["intent_count"] != len(intents):
            raise ValueError(f"{node_id}: intent_count måste matcha antal intents")
        targets = node.get("targets", [])
        ids = [target.get("target_id") for target in targets]
        count = node.get("target_count", 0)
        if count != len(ids) or len(ids) != len(set(ids)):
            raise ValueError(f"{node_id}: target_count must count unique targets")
        if state.startswith("P4"):
            allowed_counts = config["target_count_by_phase_state"][state]
            if count not in allowed_counts:
                raise ValueError(f"{node_id}: target_count är inte tillåtet för {state}")
        elif state in {"D2", "D5"}:
            allowed_counts = config["target_count_by_deviation_type"][state]
            if count not in allowed_counts:
                raise ValueError(f"{node_id}: target_count är inte tillåtet för {state}")
        for target in targets:
            target_id = target.get("target_id")
            if target_id not in active:
                raise ValueError(f"{node_id}: target {target_id} is not active earlier in flow")
            expected_mlp1 = expected_mlp1_for_target(target_id)
            if expected_mlp1 is None:
                raise ValueError(f"{node_id}: unknown target ID type: {target_id}")
            if target.get("mlp1") != expected_mlp1:
                raise ValueError(
                    f"{node_id}: {target_id} must use MLP1 {expected_mlp1}"
                )
            if target.get("mlp2") not in allowed_actions.get(target.get("mlp1"), set()):
                raise ValueError(f"{node_id}: unsupported correction action")
            if target.get("mlp1") == "Tjänster" and target.get("mlp2") == "byta ut":
                service = target.get("parameters", {}).get("service")
                if not service:
                    raise ValueError(f"{node_id}: service replacement saknar ny tjänst")
                other_services = {
                    service_id: value
                    for service_id, value in active_services.items()
                    if service_id != target_id
                }
                if service in other_services.values():
                    raise ValueError(f"{node_id}: duplicate active service after replacement")
                active_services[target_id] = service
                validate_active_services(active_services, pool_config)
        if state == "D1":
            if node.get("mlp1") != d1_rules["mlp1"]:
                raise ValueError(f"{node_id}: D1 måste använda {d1_rules['mlp1']}")
            pool = node.get("parameters", {}).get("pool")
            reference_id = node.get(d1_rules["reference_id_field"])
            if pool == d1_rules["general_pool"] and reference_id:
                raise ValueError(f"{node_id}: generell FAQ får inte ha reference_id")
            if pool in d1_rules["reference_pools"]:
                if reference_id not in active:
                    raise ValueError(f"{node_id}: FAQ reference is not active earlier in flow")
                if not reference_id.startswith(reference_prefixes[pool]):
                    raise ValueError(f"{node_id}: FAQ reference matchar inte vald pool")
            if pool not in {d1_rules["general_pool"], *d1_rules["reference_pools"]}:
                raise ValueError(f"{node_id}: okänd D1-pool")
        for intent in intents:
            intent_id = intent["intent_id"]
            mlp1 = intent.get("mlp1")
            if intent.get("mlp2") not in allowed_creators.get(mlp1, set()):
                raise ValueError(f"{node_id}: unsupported creation action")
            expected_mlp1 = expected_mlp1_for_target(intent_id)
            if expected_mlp1 != mlp1:
                raise ValueError(f"{node_id}: intent_id matchar inte MLP1")
            if intent_id in active:
                raise ValueError(f"{node_id}: intent_id finns redan")
            if intent.get("mlp1") == "Tjänster":
                service = intent.get("parameters", {}).get("service")
                if not service:
                    raise ValueError(f"{node_id}: service intent saknar tjänst")
                if service in active_services.values():
                    raise ValueError(f"{node_id}: duplicate active service")
                active_services[intent_id] = service
                validate_active_services(active_services, pool_config)
            active.add(intent_id)


def validate_correction_targets(template, config=None, pool_config=None):
    """Backward-compatible name for callers that validate corrections only."""
    validate_hierarchy(template, config, pool_config)


def d_node(source, slot, kind, config):
    payload = source["stage9"]["component_payloads"].get(slot, {})
    turns = source["stage7"]["final_turn_allocations"]["D_slot_" + slot[-1]]
    node = {
        "type": "deviation",
        "state": kind,
        "customer_turns": turns,
    }
    if kind == "D1":
        node["instruction"] = config["state_instructions"][kind]
        node["mlp1"] = "FAQ"
        node["parameters"] = {"pool": payload["pool"]}
        if "reference_id" in payload:
            node["reference_id"] = payload["reference_id"]
    elif kind == "D3":
        source_intents = payload.get("intents", [])
        node["instruction"] = config["state_instructions"][kind]
        node["intent_count"] = len(source_intents)
        node["intents"] = [
            {
                "intent_id": item["intent_id"],
                "mlp1": "Tjänster",
                "mlp2": "lägga till",
                "parameters": {"service": item["service"]},
            }
            for item in source_intents
        ]
    else:
        corrections = payload.get("corrections", [])
        node["instruction"] = config["state_instructions"][kind]
        node["target_count"] = len(corrections)
        if corrections:
            # The final prompt needs the object and action, not a prewritten correction.
            node["targets"] = clean_targets(corrections)
    return node


def build_template(source, config=None):
    config = config or load_config()
    stage9 = source["stage9"]
    nodes = {phase: phase_node(source, phase, config) for phase in ("P1", "P2", "P3", "P4", "P5")}

    p2 = p2_intents(stage9)
    if p2:
        service_count = len(p2) - 1
        allowed_counts = config["p2_service_count_by_state"][nodes["P2"]["state"]]
        if service_count not in allowed_counts:
            raise ValueError(f"P2: service_count är inte tillåtet för {nodes['P2']['state']}")
        nodes["P2"]["intent_count"] = source["stage8"]["assignments"]["P2"]["intent_count"]
        nodes["P2"]["intents"] = p2

    p3_payload = stage9["component_payloads"].get("P3")
    if p3_payload:
        nodes["P3"]["intent_count"] = source["stage8"]["assignments"]["P3"]["intent_count"]
        nodes["P3"]["intents"] = [p3_payload]

    p4_corrections = stage9["component_payloads"].get("P4", {}).get("corrections", [])
    if p4_corrections:
        nodes["P4"]["target_count"] = len(p4_corrections)
        nodes["P4"]["targets"] = clean_targets(p4_corrections)

    deviations = active_deviations(source)
    deviation_ids = deviation_node_ids(deviations)
    flow = []
    for phase in ("P1", "P2", "P3", "P4"):
        flow.append(phase)
        for slot, kind, host_phase in deviations:
            if host_phase == phase:
                node_id = deviation_ids[slot]
                if node_id in nodes:
                    raise ValueError(f"{source['template_id']} har dubbla {kind}-block.")
                nodes[node_id] = d_node(source, slot, kind, config)
                flow.append(node_id)
    # A deviation hosted at P5 happens before, never after, the closing phase.
    for slot, kind, host_phase in deviations:
        if host_phase == "P5":
            node_id = deviation_ids[slot]
            if node_id in nodes:
                raise ValueError(f"{source['template_id']} har dubbla {kind}-block.")
            nodes[node_id] = d_node(source, slot, kind, config)
            flow.append(node_id)
    flow.append("P5")

    result = {
        "template_id": source["template_id"].replace("RAW_", "T_", 1),
        "macro": {"formality": {"instruction": source["stage5"]["language_label"]}},
        "global_constraints": {
            "total_customer_turns": source["stage4"]["turn_count"],
            "strict_node_order": True,
        },
        "flow": flow,
        "nodes": nodes,
    }
    validate_hierarchy(result, config)
    return result


def main():
    parser = argparse.ArgumentParser(description="Rensar steg-9-mallar till slutlig hierarki utan ny logik.")
    parser.add_argument("--indir", default=str(DEFAULT_INPUT))
    parser.add_argument("--outdir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    indir, outdir = Path(args.indir), Path(args.outdir)
    config = load_config(args.config)
    if outdir.exists():
        shutil.rmtree(outdir)

    counts = Counter()
    for path in sorted(indir.rglob("RAW_*.json")):
        source = load_json(path)
        result = build_template(source, config)
        relative = path.relative_to(indir)
        write_json(outdir / "valid_templates" / relative, result)
        counts["GENERATED"] += 1

    write_json(outdir / "stage10_report.json", {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": dict(counts),
        "mode": "Stage 10 renderar endast data som redan finns i steg 9.",
        "config": str(Path(args.config).resolve()),
        "config_schema_version": config["schema_version"],
    })
    print(f"Stage 10 complete. Generated={counts['GENERATED']}.")


if __name__ == "__main__":
    main()
