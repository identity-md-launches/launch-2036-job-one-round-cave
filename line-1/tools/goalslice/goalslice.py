#!/usr/bin/env python3
"""Keep requested deliverables and their prerequisite closure; execute nothing."""
import argparse
from decimal import Decimal
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location(
    'goalslice_check', Path(__file__).resolve().parents[1] / 'plancheck' / 'plancheck.py')
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def exact(value):
    """Render a finite base-ten fraction without rounding or a Decimal context."""
    value = Fraction(value)
    denominator = value.denominator
    for prime in (2, 5):
        while denominator % prime == 0:
            denominator //= prime
    if denominator != 1:
        raise ValueError('not a finite decimal')
    whole, rest = divmod(value.numerator, value.denominator)
    digits = []
    while rest:
        digit, rest = divmod(rest * 10, value.denominator)
        digits.append(str(digit))
    return str(whole) + ('.' + ''.join(digits) if digits else '')


def select(data, targets):
    """Validate the entire graph, then take its minimal prerequisite-closed subset.

    Returns a report with exact minute strings. Use tasks_json(report) for
    planner-compatible JSON with exact numeric tokens rather than strings.
    """
    graph = check.graph(data)
    if (not isinstance(targets, (list, tuple)) or not 1 <= len(targets) <= 500
            or any(not isinstance(n, str) for n in targets)
            or len(set(targets)) != len(targets)):
        raise ValueError('targets must contain 1 to 500 distinct task ids')
    if any(n not in graph for n in targets):
        raise ValueError('unknown target task')
    # Separate closures explain why each prerequisite was retained. Iterative
    # traversal handles a maximum-size chain without recursion limits.
    required_by = {n: [] for n in graph}
    for target in sorted(targets):
        seen, stack = set(), [target]
        while stack:
            name = stack.pop()
            if name in seen:
                continue
            seen.add(name)
            required_by[name].append(target)
            stack.extend(graph[name][1])
    kept = sorted(n for n in graph if required_by[n])
    dropped = sorted(set(graph) - set(kept))
    return {
        'targets': sorted(targets),
        'tasks': [{'id': n, 'minutes': exact(graph[n][0]),
                   'after': sorted(graph[n][1])} for n in kept],
        'required_by': {n: required_by[n] for n in kept},
        'omitted': dropped,
        'retained_effort_minutes': exact(sum((graph[n][0] for n in kept), Fraction(0))),
        'omitted_effort_minutes': exact(sum((graph[n][0] for n in dropped), Fraction(0))),
        'scope': 'Caller-selected deliverables and declared prerequisites only; '
                 'effort is not elapsed time or a deadline guarantee; no task execution.'}


def tasks_json(report):
    # Only validated, canonical numeric strings are inserted unquoted. JSON
    # escaping remains responsible for all caller-supplied task names.
    rows = []
    for row in report['tasks']:
        decimal = Decimal(row['minutes'])
        sign, digits, exponent = decimal.as_tuple()
        digits = list(digits)
        # Retain the validator's exponent bound while compacting expanded
        # integers such as 1e100. Decimal.normalize() would round at context
        # precision and can silently change a 100-digit estimate.
        while len(digits) > 1 and digits[-1] == 0 and exponent < 100:
            digits.pop()
            exponent += 1
        decimal = Decimal((sign, tuple(digits), exponent))
        minutes = check.number(decimal, 'minutes')
        if minutes <= 0:
            raise ValueError('minutes must be positive')
        rows.append('{"id": ' + json.dumps(row['id']) + ', "minutes": '
                    + str(decimal) + ', "after": ' + json.dumps(row['after']) + '}')
    encoded = '{"tasks": [\n  ' + ',\n  '.join(rows) + '\n]}'
    if len(encoded.encode('utf-8')) > check.LIMIT:
        raise ValueError('selected graph encoding exceeds 100 KB; use fewer targets')
    return encoded


def demo():
    data = {'tasks': [
        {'id': 'brief', 'minutes': 2},
        {'id': 'build', 'minutes': 5, 'after': ['brief']},
        {'id': 'test', 'minutes': 3, 'after': ['build']},
        {'id': 'deliver', 'minutes': 1, 'after': ['test']},
        {'id': 'optional-chart', 'minutes': 8, 'after': ['brief']},
        {'id': 'optional-polish', 'minutes': 4, 'after': ['optional-chart']}]}
    return select(data, ['deliver'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--tasks')
    parser.add_argument('--target', action='append', default=[])
    parser.add_argument('--explain', action='store_true', help='report instead of planner input')
    args = parser.parse_args()
    try:
        if args.demo:
            if args.tasks is not None or args.target:
                raise ValueError('--demo cannot be combined with --tasks or --target')
            report = demo()
        else:
            if args.tasks is None:
                raise ValueError('--tasks and at least one --target are required')
            report = select(check.read_json(args.tasks), args.target)
        print(json.dumps(report, indent=2, allow_nan=False) if args.explain else tasks_json(report))
        return 0
    except (ValueError, OSError, RecursionError, OverflowError) as exc:
        print('goalslice: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
