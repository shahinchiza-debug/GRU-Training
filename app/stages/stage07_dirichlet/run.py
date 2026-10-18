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
DEFAULT_STAGE6_DIR = WORKSPACE_ROOT / "data" / "output" / "stage06_form"
DEFAULT_STAGE7_DIR = WORKSPACE_ROOT / "data" / "output" / "stage07_dirichlet"
DEFAULT_CONFIG_PATH = WORKSPACE_ROOT / "config" / "stage7_dirichlet_turn_allocation.json"


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


def sample_dirichlet_weights(rng, alpha_value, component_count):
    gamma_samples = [rng.gammavariate(alpha_value, 1.0) for _ in range(component_count)]
    total = sum(gamma_samples)
    if total == 0:
        return [1.0 / component_count] * component_count
    return [sample / total for sample in gamma_samples]


def weighted_pick(rng, keys, weights):
    threshold = rng.random()
    cumulative = 0.0
    for key, weight in zip(keys, weights):
        cumulative += weight
        if threshold <= cumulative:
            return key
    return keys[-1]


def active_variable_components(template, config):
    components = list(config["always_active_variable_components"])
    for slot_key in ["D_1", "D_2"]:
        if template.get(slot_key, {}).get("state"):
            components.append(config["deviation_slot_to_component"][slot_key])
    return components


def fixed_turn_allocations(template):
    stage6 = template["stage6"]
    return dict(stage6["fixed_phase_turns"])


def annotate_invalid_stage7(template, active_components, total_turn_budget, fixed_allocations, reason_code, reason):
    annotated = dict(template)
    locked_total = sum(fixed_allocations.values())
    annotated["stage7"] = {
        "valid": False,
        "reason_code": reason_code,
        "reason": reason,
        "total_turn_budget": total_turn_budget,
        "locked_phase_turns": fixed_allocations,
        "locked_turn_total": locked_total,
        "remaining_turn_budget": total_turn_budget - locked_total,
        "active_variable_components": active_components,
        "minimum_turn_floor_per_active_component": 1,
        "minimum_required_variable_turns": len(active_components)
    }
    return annotated


def annotate_valid_stage7(template, config):
    total_turn_budget = int(template["stage5"]["turn_count"])
    fixed_allocations = fixed_turn_allocations(template)
    locked_total = sum(fixed_allocations.values())
    remaining_turn_budget = total_turn_budget - locked_total
    active_components = active_variable_components(template, config)
    minimum_required_variable_turns = len(active_components)

    if remaining_turn_budget < minimum_required_variable_turns:
        return False, annotate_invalid_stage7(
            template=template,
            active_components=active_components,
            total_turn_budget=total_turn_budget,
            fixed_allocations=fixed_allocations,
            reason_code="INSUFFICIENT_REMAINING_TURNS",
            reason=(
                f"Turnbudget {total_turn_budget} racker inte for {minimum_required_variable_turns} aktiva rorliga delar "
                f"nar lasta turer summerar till {locked_total}."
            ),
        )

    rng = build_rng(config["random_seed_namespace"], template["template_id"])
    extra_token_budget = remaining_turn_budget - minimum_required_variable_turns
    alpha_value = float(config["alpha_by_turn_count"][str(total_turn_budget)])
    weights = sample_dirichlet_weights(rng, alpha_value, len(active_components))

    variable_turn_allocations = {component: 1 for component in active_components}
    for _ in range(extra_token_budget):
        chosen_component = weighted_pick(rng, active_components, weights)
        variable_turn_allocations[chosen_component] += 1

    final_turn_allocations = dict(fixed_allocations)
    final_turn_allocations.update(variable_turn_allocations)

    annotated = dict(template)
    annotated["stage7"] = {
        "valid": True,
        "total_turn_budget": total_turn_budget,
        "locked_phase_turns": fixed_allocations,
        "locked_turn_total": locked_total,
        "remaining_turn_budget": remaining_turn_budget,
        "active_variable_components": active_components,
        "minimum_turn_floor_per_active_component": config["minimum_turn_floor_per_active_component"],
        "minimum_required_variable_turns": minimum_required_variable_turns,
        "extra_token_budget": extra_token_budget,
        "alpha_value": alpha_value,
        "alpha_vector": [alpha_value] * len(active_components),
        "dirichlet_weights": {
            component: weight
            for component, weight in zip(active_components, weights)
        },
        "variable_turn_allocations": variable_turn_allocations,
        "final_turn_allocations": final_turn_allocations
    }
    return True, annotated


def write_stage7_readme(outdir):
    readme_text = """# Stage 7 Output

Steg 7 lagger till faktisk turfordelning med Dirichlet.

Input:

- `data/output/stage06_form/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Output:

- giltiga mallar: `data/output/stage07_dirichlet/valid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`
- ogiltiga mallar: `data/output/stage07_dirichlet/invalid_templates/<sprak>/turn_<antal>/<formprofil>/RAW_*.json`

Vad som hander:

- `P1`, `P3` och `P5` behaller sina lasta turer fran steg 6
- `P2` och `P4` ar alltid aktiva rorliga delar
- aktiv `D_1` blir `D_slot_1` och behaller sin D-typ fran mallen
- aktiv `D_2` blir `D_slot_2` och behaller sin D-typ fran mallen
- varje aktiv rorlig del far minst `1` tur
- resterande turer fordelas token-for-token med symmetrisk Dirichlet
"""
    (outdir / "README.md").write_text(readme_text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Allocate stage-7 turn counts with Dirichlet weighting."
    )
    parser.add_argument(
        "--indir",
        default=str(DEFAULT_STAGE6_DIR),
        help="Directory containing stage-6 output.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to stage7_dirichlet_turn_allocation.json.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_STAGE7_DIR),
        help="Directory for stage-7 output.",
    )
    args = parser.parse_args()

    indir = Path(args.indir)
    config = load_json(args.config)
    outdir = Path(args.outdir)
    valid_dir = outdir / "valid_templates"
    invalid_dir = outdir / "invalid_templates"

    clear_output_dir(outdir)
    write_stage7_readme(outdir)

    valid_count = 0
    invalid_count = 0
    invalid_reason_counts = Counter()
    totals_by_turn = Counter()
    totals_by_form_profile = Counter()

    for template_path in sorted(indir.rglob("RAW_*.json")):
        template = load_json(template_path)
        relative_path = template_path.relative_to(indir)
        is_valid, annotated = annotate_valid_stage7(template, config)

        target_root = valid_dir if is_valid else invalid_dir
        write_template(target_root / relative_path, annotated)

        turn_count = int(template["stage5"]["turn_count"])
        form_profile = template["stage6"]["form_profile"]
        totals_by_turn[turn_count] += 1 if is_valid else 0
        totals_by_form_profile[form_profile] += 1 if is_valid else 0

        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            invalid_reason_counts[annotated["stage7"]["reason_code"]] += 1

    report_payload = {
        "processed_template_count": valid_count + invalid_count,
        "valid_template_count": valid_count,
        "invalid_template_count": invalid_count,
        "invalid_reason_counts": dict(sorted(invalid_reason_counts.items())),
        "valid_totals_by_turn": dict(sorted(totals_by_turn.items())),
        "valid_totals_by_form_profile": dict(sorted(totals_by_form_profile.items()))
    }
    write_json(outdir / "stage7_turn_allocation_report.json", report_payload)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(indir),
        "config_path": str(Path(args.config)),
        "output_directory": str(outdir),
        "valid_template_count": valid_count,
        "invalid_template_count": invalid_count
    }
    write_json(outdir / "stage7_metadata.json", metadata_payload)

    print(
        f"Stage 7 complete. Valid={valid_count}, invalid={invalid_count}."
    )


if __name__ == "__main__":
    main()
