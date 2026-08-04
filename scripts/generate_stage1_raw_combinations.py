import argparse
import json
from datetime import datetime, timezone
from itertools import product
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_STRUCTURE_PATH = PROJECT_ROOT / "input" / "structure.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "stage1_output"
RAW_TEMPLATES_DIRNAME = "raw_templates"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def make_deviation_item(type_config, phase):
    return {
        "type": type_config["type_id"],
        "phase": phase,
        "state": f"{type_config['type_id']}@{phase}",
        "template_value": f"{type_config['template_value_base']}_{phase.lower()}",
        "description": f"{type_config['description']} i {phase}.",
    }


def build_atomic_deviation_options(d_space):
    options = []
    for type_config in d_space["active_types"]:
        for phase in type_config["allowed_phases"]:
            options.append(make_deviation_item(type_config, phase))

    expected_options = d_space["generation_rules"]["one_deviation"]["expected_atomic_options"]
    if len(options) != expected_options:
        raise ValueError(f"Expected {expected_options} atomic deviation options, got {len(options)}")

    return options


def generate_deviation_configs(structure):
    d_space = structure["d_space"]
    atomic_options = build_atomic_deviation_options(d_space)

    configs = []
    config_index = 1

    def add_config(slot_1, slot_2):
        nonlocal config_index
        deviation_count = int(slot_1 is not None) + int(slot_2 is not None)

        configs.append(
            {
                "config_id": f"D_CFG_{config_index:03d}",
                "deviation_count": deviation_count,
                "d_1": slot_1["state"] if slot_1 else d_space["empty_value"],
                "d_2": slot_2["state"] if slot_2 else d_space["empty_value"],
                "slot_meta": {
                    "d_1": slot_1,
                    "d_2": slot_2,
                },
            }
        )
        config_index += 1

    add_config(None, None)

    for item in atomic_options:
        add_config(item, None)

    for slot_1, slot_2 in product(atomic_options, repeat=2):
        add_config(slot_1, slot_2)

    expected_count = d_space["expected_count"]
    if len(configs) != expected_count:
        raise ValueError(f"Expected {expected_count} raw deviation configs, got {len(configs)}")

    return configs


def generate_raw_templates(structure):
    p_categories = structure["p_space"]["categories"]
    p_keys = ["p1", "p2", "p3", "p4", "p5"]
    p_lists = [p_categories[key] for key in p_keys]
    d_configs = generate_deviation_configs(structure)
    p_combinations = [dict(zip(p_keys, values)) for values in product(*p_lists)]
    return p_combinations, d_configs


def build_template(template_index, p_map, d_config):
    return {
        "template_id": f"RAW_{template_index:06d}",
        "P1": {
            "state": p_map["p1"]["state_id"],
            "desc": p_map["p1"]["description"],
        },
        "P2": {
            "state": p_map["p2"]["state_id"],
            "desc": p_map["p2"]["description"],
        },
        "P3": {
            "state": p_map["p3"]["state_id"],
            "desc": p_map["p3"]["description"],
        },
        "P4": {
            "state": p_map["p4"]["state_id"],
            "desc": p_map["p4"]["description"],
        },
        "P5": {
            "state": p_map["p5"]["state_id"],
            "desc": p_map["p5"]["description"],
        },
        "D_1": {
            "state": d_config["slot_meta"]["d_1"]["state"] if d_config["slot_meta"]["d_1"] else None,
            "desc": d_config["slot_meta"]["d_1"]["description"] if d_config["slot_meta"]["d_1"] else "Ingen avvikelse",
        },
        "D_2": {
            "state": d_config["slot_meta"]["d_2"]["state"] if d_config["slot_meta"]["d_2"] else None,
            "desc": d_config["slot_meta"]["d_2"]["description"] if d_config["slot_meta"]["d_2"] else "Ingen avvikelse",
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic raw stage-1 P/D templates before any filtering.")
    parser.add_argument("--structure", default=str(DEFAULT_STRUCTURE_PATH), help="Path to input structure.json")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for stage-1 output files")
    parser.add_argument("--limit", type=int, help="Optional debug limit. If omitted, the full raw space is generated.")
    args = parser.parse_args()

    structure_path = Path(args.structure)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    raw_templates_dir = outdir / RAW_TEMPLATES_DIRNAME
    raw_templates_dir.mkdir(parents=True, exist_ok=True)

    structure = load_json(structure_path)
    p_combinations, d_configs = generate_raw_templates(structure)

    p_count = len(p_combinations)
    d_count = len(d_configs)
    max_unique_space = p_count * d_count
    requested_count = args.limit if args.limit is not None else max_unique_space

    if requested_count < 1:
        raise ValueError("--limit must be at least 1")
    if requested_count > max_unique_space:
        raise ValueError(f"Requested {requested_count} templates, but max unique raw space is {max_unique_space}")

    for existing_file in raw_templates_dir.glob("RAW_*.json"):
        existing_file.unlink()

    for stale_file in [
        outdir / "stage1_statistics.json",
        outdir / "stage1_statistics.md",
        outdir / "stage1_comparison.json",
        outdir / "stage1_comparison.md",
    ]:
        if stale_file.exists():
            stale_file.unlink()

    templates = []
    template_index = 1
    for p_map, d_config in product(p_combinations, d_configs):
        templates.append(build_template(template_index, p_map, d_config))
        template_index += 1
        if len(templates) >= requested_count:
            break

    for template in templates:
        write_json(raw_templates_dir / f"{template['template_id']}.json", template)

    metadata_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "structure_path": str(structure_path),
        "output_directory": str(outdir),
        "raw_templates_directory": str(raw_templates_dir),
        "logic_filter_applied": structure["logic_filter_applied"],
        "generation_mode": "deterministic_full_enumeration",
        "p_count": p_count,
        "d_count": d_count,
        "max_unique_template_space": max_unique_space,
        "generated_template_count": len(templates),
        "full_space_generated": requested_count == max_unique_space,
        "limit_used": args.limit,
        "first_template_id": templates[0]["template_id"] if templates else None,
        "last_template_id": templates[-1]["template_id"] if templates else None,
        "warnings": [] if requested_count == max_unique_space else [
            "Debug limit used. Output is a truncated prefix of the full deterministic raw space."
        ],
    }

    write_json(outdir / "stage1_metadata.json", metadata_payload)

    print(f"Generated {len(templates)} deterministic raw stage-1 templates in {raw_templates_dir}")


if __name__ == "__main__":
    main()
