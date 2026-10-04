import argparse
import json

from pipeline.catalog import DEFAULT_MANIFEST_PATH, load_stage_specs
from pipeline.orchestrator import run_pipeline


def build_parser():
    parser = argparse.ArgumentParser(
        description="Central huvudfunktion for den modulara training-template-pipelinen."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH), help="Path to pipeline manifest JSON.")
    parser.add_argument("--list", action="store_true", help="Lista alla tillgangliga steg.")
    parser.add_argument("--show", metavar="STAGE", help="Visa detaljer for ett specifikt steg.")
    parser.add_argument("--from", dest="start_stage", metavar="STAGE", help="Koer fran detta steg.")
    parser.add_argument("--to", dest="end_stage", metavar="STAGE", help="Koer till detta steg.")
    parser.add_argument("--only", nargs="+", help="Koer bara angivna steg. Kan anges som lista eller kommaseparerat.")
    parser.add_argument("--skip", nargs="+", help="Hoppa over angivna steg. Kan anges som lista eller kommaseparerat.")
    parser.add_argument("--dry-run", action="store_true", help="Visa vad som skulle koras utan att faktiskt koera nagot.")
    parser.add_argument("--continue-on-error", action="store_true", help="Fortsatt koera resterande steg aven om ett steg faller.")
    return parser


def print_stage_list(stage_specs):
    print("Tillgangliga steg:\n")
    for spec in stage_specs:
        print(f"{spec.order}. {spec.key} - {spec.label}")
        print(f"   Script: {spec.script_path}")
        print(f"   Beskrivning: {spec.description}")


def print_stage_details(stage_specs, stage_key):
    stage_map = {spec.key: spec for spec in stage_specs}
    if stage_key not in stage_map:
        raise ValueError(f"Okant steg: {stage_key}")

    print(json.dumps(stage_map[stage_key].to_dict(), indent=2, ensure_ascii=False))


def print_run_summary(report):
    print("")
    print(f"Valda steg: {', '.join(report['selected_stage_keys'])}")
    print(f"Klara steg: {', '.join(report['completed_stage_keys'])}")
    print(f"Alla lyckades: {report['all_successful']}")
    if "report_paths" in report:
        print(f"Rapport: {report['report_paths']['latest']}")
    print("")

    for result in report["results"]:
        print(f"- {result['key']} [{result['status']}] {result['duration_seconds']}s")
        if result.get("missing_inputs"):
            print(f"  missing_inputs: {', '.join(result['missing_inputs'])}")
        if result["stdout"]:
            print(f"  stdout: {result['stdout']}")
        if result["stderr"]:
            print(f"  stderr: {result['stderr']}")


def main():
    parser = build_parser()
    args = parser.parse_args()
    stage_specs = load_stage_specs(args.manifest)

    if args.list:
        print_stage_list(stage_specs)
        return

    if args.show:
        print_stage_details(stage_specs, args.show)
        return

    report = run_pipeline(
        manifest_path=args.manifest,
        only=args.only,
        start=args.start_stage,
        end=args.end_stage,
        skip=args.skip,
        dry_run=args.dry_run,
        continue_on_error=args.continue_on_error,
    )
    print_run_summary(report)


if __name__ == "__main__":
    main()
