#!/usr/bin/env python3
"""Finite identifier oracle and CLI regressions, no network."""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import idcheck as i

ABSENT = object()


def doc(identifier=ABSENT):
    op = {'responses': {}}
    if identifier is not ABSENT:
        op['operationId'] = identifier
    return {'openapi': '3.1.0', 'paths': {'/a~b/c': {'get': op}}}


def codes(a, b):
    return {f['code'] for f in i.compare(a, b)['findings']}


class Checks(unittest.TestCase):
    def test_capture_and_demo(self):
        capture = Path(__file__).resolve().parents[1] / 'apidelta' / 'imd-openapi.json'
        a, _ = i.api.load(capture)
        self.assertEqual(i.compare(a, a)['findings'], [])
        self.assertEqual(i.demo()['counts'], {'breaking': 1, 'review': 1, 'info': 0})

    def test_finite_oracle(self):
        # All 36 pairs, including absent, empty, case-sensitive and Unicode IDs.
        values = [ABSENT, '', 'getThing', 'GetThing', '雪', 'odd/name~id']
        for old, new in itertools.product(values, repeat=2):
            with self.subTest(old=old, new=new):
                found = codes(doc(old), doc(new))
                expected = set()
                if old != new:
                    expected = {'operation_id_added' if old is ABSENT else
                                'operation_id_removed' if new is ABSENT else 'operation_id_changed'}
                self.assertEqual({c for c in found if c.startswith('operation_id_')}, expected)

    def test_duplicate_all_paths_methods(self):
        a = doc('same')
        for path, method in [('/other', 'get'), ('/a~b/c', 'post')]:
            b = copy.deepcopy(a)
            b['paths'].setdefault(path, {})[method] = {'operationId': 'same', 'responses': {}}
            with self.assertRaises(i.api.Invalid):
                i.compare(a, b)
            with self.assertRaises(i.api.Invalid):
                i.compare(b, a)

    def test_duplicate_empty_and_case_sensitive(self):
        a = doc('')
        a['paths']['/other'] = {'get': {'operationId': '', 'responses': {}}}
        with self.assertRaises(i.api.Invalid):
            i.compare(a, a)
        a = doc('read')
        a['paths']['/other'] = {'get': {'operationId': 'Read', 'responses': {}}}
        self.assertEqual(i.compare(a, a)['findings'], [])

    def test_invalid_on_added_removed_and_identical(self):
        for invalid in [None, False, 42, [], {}, 'x' * 4097]:
            b = doc(invalid)
            for old, new in [(b, b), ({'openapi': '3.1.0', 'paths': {}}, b),
                             (b, {'openapi': '3.1.0', 'paths': {}})]:
                with self.subTest(invalid=type(invalid).__name__), self.assertRaises(i.api.Invalid):
                    i.compare(old, new)

    def test_invalid_operations(self):
        for operation in [None, [], {'$ref': '#/components/operations/a'}]:
            a = doc()
            a['paths']['/a~b/c']['get'] = operation
            with self.assertRaises(i.api.Invalid):
                i.compare(a, a)

    def test_multiple_absent_and_max_length(self):
        a = doc()
        a['paths']['/other'] = {'get': {'responses': {}}}
        self.assertEqual(i.compare(a, a)['findings'], [])
        a = doc('x' * 4096)
        self.assertEqual(i.compare(a, a)['findings'], [])

    def test_no_root_or_path_inheritance(self):
        a = doc()
        a['operationId'] = 'root'
        a['paths']['/a~b/c']['operationId'] = 'path'
        b = copy.deepcopy(a)
        b['operationId'] = 'changed'
        self.assertFalse(any(c.startswith('operation_id_') for c in codes(a, b)))

    def test_callbacks_and_webhooks_scope_explicit(self):
        a = doc('read')
        a['webhooks'] = {'event': {'post': {'operationId': 'read'}}}
        a['paths']['/a~b/c']['get']['callbacks'] = {'cb': {}}
        result = i.compare(a, a)
        self.assertEqual(result['findings'], [])
        self.assertIn('callbacks and webhooks excluded', result['identifier_scope'])

    def test_operation_limit(self):
        limit = i.MAX_OPERATIONS
        i.MAX_OPERATIONS = 0
        try:
            with self.assertRaises(i.api.Invalid):
                i.compare(doc(), doc())
        finally:
            i.MAX_OPERATIONS = limit

    def test_retained_findings_nonmutation_and_pointer(self):
        a, b = doc('old'), doc('new')
        b['servers'] = [{'url': '/new'}]
        before = copy.deepcopy((a, b))
        result = i.compare(a, b)
        self.assertTrue(all(f in result['findings'] for f in i.server.compare(a, b)['findings']))
        self.assertEqual((a, b), before)
        self.assertEqual(i.compare(a, b), result)
        self.assertTrue(any(f['location'] == '/paths/~1a~0b~1c/get/operationId'
                            for f in result['findings']))

    def test_swap_identifiers(self):
        a = doc('one')
        a['paths']['/other'] = {'get': {'operationId': 'two', 'responses': {}}}
        b = copy.deepcopy(a)
        b['paths']['/a~b/c']['get']['operationId'] = 'two'
        b['paths']['/other']['get']['operationId'] = 'one'
        self.assertEqual(sum(f['code'] == 'operation_id_changed' for f in i.compare(a, b)['findings']), 2)

    def test_cli_outcomes(self):
        root = Path('test/scratch')
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            a, b = Path(tmp) / 'a.json', Path(tmp) / 'b.json'
            for old, new, expected in [(doc('old'), doc('old'), 0), (doc('old'), doc('new'), 1),
                                       (doc(), doc('new'), 3), (doc('old'), doc(None), 2)]:
                a.write_text(json.dumps(old))
                b.write_text(json.dumps(new))
                run = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('idcheck.py')),
                                      'compare', str(a), str(b)], capture_output=True, text=True, timeout=15)
                self.assertEqual(run.returncode, expected, run.stderr)
                if expected != 2:
                    self.assertEqual(len(json.loads(run.stdout)['old_sha256']), 64)
                else:
                    self.assertEqual(run.stdout, '')


if __name__ == '__main__':
    unittest.main()
