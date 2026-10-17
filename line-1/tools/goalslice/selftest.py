"""Independent closure, exact numeric round-trip, and planner integration checks."""
import copy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

import goalslice as tool


class GoalsliceTests(unittest.TestCase):
    def test_demo(self):
        report = tool.demo()
        self.assertEqual(report['omitted'], ['optional-chart', 'optional-polish'])
        self.assertEqual(report['retained_effort_minutes'], '11')
        self.assertEqual(report['omitted_effort_minutes'], '12')
        self.assertEqual(report['required_by']['brief'], ['deliver'])

    def test_shared_prerequisite_and_target_ancestor(self):
        data = {'tasks': [{'id': 'a', 'minutes': 1},
                          {'id': 'b', 'minutes': 2, 'after': ['a']},
                          {'id': 'c', 'minutes': 3, 'after': ['a']}]}
        report = tool.select(data, ['b', 'c', 'a'])
        self.assertEqual(report['required_by']['a'], ['a', 'b', 'c'])
        self.assertEqual(report['retained_effort_minutes'], '6')
        self.assertEqual(report['omitted'], [])

    def test_invalid_whole_graph_even_when_not_selected(self):
        for extra in ({'id': 'b', 'minutes': 1, 'after': ['b']},
                      {'id': 'b', 'minutes': 0},
                      {'id': 'b', 'minutes': 1, 'after': ['missing']}):
            with self.assertRaises(ValueError):
                tool.select({'tasks': [{'id': 'a', 'minutes': 1}, extra]}, ['a'])

    def test_invalid_targets(self):
        data = {'tasks': [{'id': 'a', 'minutes': 1}]}
        for targets in ([], ['a', 'a'], ['missing'], 'a', [True], ['a'] * 501):
            with self.assertRaises(ValueError):
                tool.select(data, targets)

    def test_exact_roundtrip_extremes_and_escaping(self):
        estimates = ['0.1', '0.2', '1e-100', '1e100', '9' * 100 + 'e100',
                     '0.' + '1234567890' * 10]
        data = {'tasks': [{'id': 'quote"\n雪' + str(i), 'minutes': Decimal(n)}
                          for i, n in enumerate(estimates)]}
        report = tool.select(data, [r['id'] for r in data['tasks']])
        encoded = tool.tasks_json(report)
        decoded = json.loads(encoded, parse_float=Decimal)
        self.assertEqual(tool.check.graph(decoded), tool.check.graph(data))
        self.assertEqual(Decimal(report['retained_effort_minutes']),
                         Decimal(tool.exact(sum(v[0] for v in tool.check.graph(data).values()))))

    def test_seeded_independent_reachability(self):
        rng = random.Random(73731)
        for _ in range(200):
            count = rng.randint(1, 30)
            rows = [{'id': str(i), 'minutes': rng.randint(1, 9),
                     'after': [str(j) for j in range(i) if rng.random() < .15]}
                    for i in range(count)]
            targets = rng.sample([r['id'] for r in rows], rng.randint(1, count))
            data = {'tasks': rows}
            original = copy.deepcopy(data)
            # Independent fixed-point set union, rather than target traversals.
            expected = set(targets)
            while True:
                grown = expected | {d for r in rows if r['id'] in expected for d in r['after']}
                if grown == expected:
                    break
                expected = grown
            report = tool.select(data, targets)
            self.assertEqual({r['id'] for r in report['tasks']}, expected)
            self.assertEqual(data, original)
            self.assertEqual(report, tool.select({'tasks': list(reversed(rows))}, list(reversed(targets))))
            selected = json.loads(tool.tasks_json(report), parse_float=Decimal)
            self.assertEqual(set(tool.check.graph(selected)), expected)

    def test_maximum_chain(self):
        data = {'tasks': [{'id': str(i), 'minutes': 1,
                           'after': [] if i == 0 else [str(i-1)]} for i in range(500)]}
        self.assertEqual(len(tool.select(data, ['499'])['tasks']), 500)
        self.assertEqual(len(tool.select(data, ['0'])['tasks']), 1)

    def test_emission_bound(self):
        data = {'tasks': [{'id': '雪' * 95 + str(i), 'minutes': 1} for i in range(500)]}
        report = tool.select(data, [r['id'] for r in data['tasks']])
        with self.assertRaisesRegex(ValueError, '100 KB'):
            tool.tasks_json(report)

    def test_planner_integration(self):
        path = Path(__file__).resolve().parents[1] / 'workplan' / 'workplan.py'
        spec = importlib.util.spec_from_file_location('goalslice_workplan', path)
        planner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(planner)
        selected = json.loads(tool.tasks_json(tool.demo()))
        plan = planner.plan(selected, workers=2, budget=12)
        self.assertEqual(plan['finish'], 11)
        self.assertTrue(tool.check.check(selected, plan, 2, 12)['valid'])

    def test_cli_and_reader_refusals(self):
        root = Path('test/scratch/goalslice')
        root.mkdir(parents=True, exist_ok=True)
        fixtures = {
            'tasks.json': '{"tasks":[{"id":"a","minutes":0.1}]}',
            'duplicate.json': '{"tasks":[],"tasks":[]}',
            'large.json': ' ' * 100001}
        for name, content in fixtures.items():
            (root / name).write_text(content)
        script = str(Path(__file__).with_name('goalslice.py'))
        cases = [(['--demo'], 0), (['--demo', '--explain'], 0),
                 (['--demo', '--target', 'a'], 1),
                 (['--tasks', str(root / 'tasks.json'), '--target', 'a'], 0),
                 (['--tasks', str(root / 'tasks.json')], 1),
                 (['--tasks', str(root / 'duplicate.json'), '--target', 'a'], 1),
                 (['--tasks', str(root / 'large.json'), '--target', 'a'], 1)]
        for args, expected in cases:
            result = subprocess.run([sys.executable, '-B', script] + args,
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            if expected:
                self.assertEqual(result.stdout, '')
            else:
                json.loads(result.stdout, parse_float=Decimal)


if __name__ == '__main__':
    unittest.main()
