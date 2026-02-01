from __future__ import annotations

import argparse

from dbmon.alerts import evaluate_rules, load_rules
from dbmon.collector import collect_from_sql, collect_mock
from dbmon.elastic import create_client, index_events
from dbmon.sample_loader import read_jsonl
from dbmon.settings import settings
from dbmon.stress import generate_events, write_jsonl


def cmd_collect() -> None:
    if settings.collector_mode == "live":
        events = collect_from_sql()
    else:
        sample_events = read_jsonl(settings.sample_input_path)
        events = collect_mock(sample_events)

    client = create_client()
    index_events(client, settings.elastic_index_metrics, events)

    rules = load_rules(settings.alert_rules_path)
    alerts = evaluate_rules(events, rules)
    index_events(client, settings.elastic_index_alerts, alerts)


def cmd_generate_stress(count: int, output: str) -> None:
    events = generate_events(count)
    write_jsonl(output, events)


def cmd_load_samples(path: str) -> None:
    events = read_jsonl(path)
    client = create_client()
    index_events(client, settings.elastic_index_metrics, events)


def main() -> None:
    parser = argparse.ArgumentParser(description="DBMon automation CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("collect", help="Collect metrics and push to Elastic")

    stress = sub.add_parser("stress", help="Generate stress-test sample metrics")
    stress.add_argument("--count", type=int, default=1000)
    stress.add_argument("--output", type=str, default="sample_inputs/stress_metrics.jsonl")

    load = sub.add_parser("load-samples", help="Load sample metrics into Elastic")
    load.add_argument("--path", type=str, default="sample_inputs/sample_metrics.jsonl")

    args = parser.parse_args()

    if args.command == "collect":
        cmd_collect()
    elif args.command == "stress":
        cmd_generate_stress(args.count, args.output)
    elif args.command == "load-samples":
        cmd_load_samples(args.path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
