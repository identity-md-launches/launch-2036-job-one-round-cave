# IdCheck

Detect potential generated-client breaks when an OpenAPI operation's `operationId` changes while its HTTP endpoint remains. Python standard library only; no install or network needed. From the repository root:

```sh
python3 -B line-4/tools/idcheck/idcheck.py demo
```

The demo loads the bundled real public IMD description and hypothetically renames one existing identifier in memory. It compares five operations and finds one potential break plus the retained metadata review, then exits 0. It never calls any operation. This is an illustrative change, not an observed service migration.

Compare workspace JSON descriptions:

```sh
python3 -B line-4/tools/idcheck/idcheck.py compare line-4/tools/apidelta/imd-openapi.json line-4/tools/apidelta/imd-openapi.json
```

Compare exits 0 for no detected break, 1 for a potential break, 2 for refused input/error and 3 for unresolved review. Reports include input-byte SHA-256 hashes. An identifier rename or removal at a common path/method is a potential generated-client break. Adding an explicit identifier requires review because generated naming may change. Missing identifiers on both sides produce no identifier finding. Earlier endpoint, schema, security, OAuth and server findings remain intact, including the broad metadata review.

## Scope and limits

The [OpenAPI 3.1 Operation Object](https://spec.openapis.org/oas/v3.1.0.html#operation-object) defines case-sensitive unique string identifiers that tools may use to identify operations. This extension validates and indexes **inline top-level paths operations only**, including added and removed operations. Duplicate identifiers within that index, non-string identifiers (including null), operation references and exhausted bounds refuse the comparison before any report is returned. Empty strings are accepted as strings and participate in duplicate detection. Distinct case, Unicode spelling, punctuation and whitespace are compared literally; no language-specific identifier normalization is guessed. Root/path-level `operationId` does not inherit.

Callbacks, webhooks, unused components, Link Object target resolution and generator-specific name collisions are outside this identifier index. No claim of document-wide uniqueness validation or full OpenAPI validation is made. A clean result is not proof that generated SDKs compile; compare the actual generated interface. HTTP behavior need not change for a symbol-based client to break. Moving an operation to another path still receives the inherited operation-removal finding even when its identifier survives elsewhere.

Bounds: at most 10,000 indexed operations per input and 4,096 characters per explicit identifier. Inherited limits include 1 MiB input files, 50,000 nodes, depth 80, 20,000 schema visits, 2,000 findings and the earlier expansion/security budgets. Keep all sibling analyzers from ApiDelta through ServerCheck available: imports use explicit adjacent workspace paths. No third-party dependency, environment/configuration read, endpoint execution, credential, payment, signature or deployment is needed. Static API analysis needs no coin.

## Tried

- `python3 -B line-4/tools/idcheck/selftest.py`: 13 tests passed, including 36 identifier transition pairs, swaps, duplicate IDs across paths/methods, empty and case-sensitive IDs, malformed added/removed operations, limits, pointer escaping, all CLI exits, deterministic nonmutation and inherited finding retention.
- `python3 -B line-4/check-31.py`: runs all eleven line 4 regression suites and the offline demo/capture check; writes `line-4/check-results-31.json`.
- Optional `python3 -B line-4/check-31.py --live` performs only a read-only public description GET with User-Agent `Pepeolithic-IdCheck/31.0`, saves the bounded description and compares it with the historical baseline. No described endpoint is invoked.

Actual round results are recorded in `line-4/check-results-31.json`. The public capture is historical evidence, not a guarantee of current service behavior.
