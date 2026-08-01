# E01 Research Reset — 2026-08-01

## Decision

**Pause and redesign the E01 composition line. Do not stop the project.**

The current generator and score-fusion experiments have completed their role as positive controls. The next stage must test whether a support-aware primitive interface is useful under imperfect recovery, meaningful headroom, multiple declared query forms and unsupported-query conditions.

## What we currently believe

### Still supported

- The committed E01 measurements are numerically reproducible under their implemented contracts.
- Keeping several nearly perfect predicted primitive coordinates separate preserves more information for a weighted product-space oracle than the two tested one-dimensional projections.
- The repository's evidence, replay and immutable-audit infrastructure is valuable.
- The original problem remains real: a frozen representation may support some relation-specific queries and not others, and a trustworthy system should identify that boundary.

### No longer accepted as the best interpretation

- E01.2a's narrow cross-seed variation is not strong evidence of robustness; it may primarily reflect saturation.
- The wrong-permutation margin is not a direct semantic-identity test in a generator with exchangeable primitives.
- E01.2a did not confirm E01.1's original `0.10` decision rule.
- `scientific gate: PASS` is too broad for a substage that attempted only one positive-control slice of the complete E01.2 design.
- The current E01 line does not establish general primitive-operator composition.

## Revised thesis

> **RELATE is a support-aware relational query runtime over frozen representations. It learns evidence-bearing primitive relations, executes declared compound queries over those primitives without retraining for every query, propagates uncertainty through the query, and refuses when the primitive evidence or query algebra is insufficient.**

This thesis separates four concerns:

1. **Primitive evidence** — named relation readouts with supervision, calibration, provenance, supported regions and failure tests.
2. **Query algebra** — declared operators such as weighted distance, conjunction, exclusion, lexicographic order and Pareto frontier.
3. **Execution** — ranking, feasible set, frontier or refusal produced from the primitive interface.
4. **Support** — a compound-level decision derived from primitive quality, shift, uncertainty and algebraic sufficiency.

## Replacement synthetic stage

### E02 — Factorisation Sufficiency and Query-Algebra Boundary

Central question:

> Given imperfect independently learned primitive relations, when is post-training query execution sufficient, when is direct compound supervision superior, and can the system detect queries outside the supported primitive algebra?

### Generator requirements

The new generator must avoid saturation and exchangeability.

Include primitives with different:

- marginal distributions;
- scales;
- noise levels;
- recoverability;
- sample requirements;
- shifts;
- local versus global support.

Required roles:

| Primitive | Role |
|---|---|
| `a` | strong, reliable primitive |
| `b` | moderately recoverable primitive |
| `c` | nonlinear or learner-family-boundary primitive |
| `d` | absent primitive |
| `e` | development-supported, test-shifted primitive |

Target primitive quality should include approximate `R²` levels around `0.3`, `0.5`, `0.7` and `0.9`.

No composition claim should be promoted from a regime where the predicted-primitive executor already exceeds `0.90–0.95` of the attainable primitive-interface ceiling.

### Query families

#### Decomposable

- weighted Euclidean distance;
- max-distance conjunction;
- threshold intersection;
- close in `a`, far in `c`;
- lexicographic ranking;
- Pareto retrieval.

Each query must use its declared operation. One fixed metric is not expected to approximate every query family.

#### Outside the registered algebra

- interaction requiring an unregistered latent variable;
- query requiring an absent primitive;
- query requiring a shifted primitive;
- interaction not expressible through the registered primitive interface.

Possible outcomes:

```text
SUPPORTED
UNSUPPORTED_AT_THRESHOLD
INSUFFICIENT_EVIDENCE
QUERY_OUTSIDE_REGISTERED_ALGEBRA
```

### Required comparisons

For each query family:

1. noiseless true-primitive executor;
2. predicted-primitive executor;
3. direct compound model at compound-supervision budgets `0`, `50`, `200`, `1000`, and full;
4. raw cosine and Euclidean;
5. conventional conditional metric-learning baseline;
6. independent primitive-thresholding baseline.

The central trade-off is not necessarily maximum accuracy. It is whether the primitive route provides useful zero-compound-example execution, reuse, provenance, calibration and failure localisation.

### Required measurements

- triplet accuracy;
- hard-negative and easy-triplet accuracy separately;
- recall@10, 25, 50 and 100;
- oracle-neighbour rank;
- neighbour regret;
- constraint satisfaction;
- direct-compound gap;
- ceiling fraction;
- compound-label data-efficiency curve;
- risk-coverage curve when refusal is later introduced.

## Kill conditions

Stop or relocate the composition line if:

1. a directly trained compound model with very few examples consistently matches or exceeds the primitive executor without losing meaningful calibration, provenance or compute advantages;
2. compound performance is only a deterministic reflection of primitive prediction quality;
3. the executor confidently answers queries using absent, out-of-family, shifted or unregistered evidence;
4. ordinary independent primitive thresholding matches compound support propagation at equal coverage;
5. the effect disappears on a carefully selected real frozen representation.

## Plausible novelty candidate

The strongest remaining candidate is:

> Propagating calibrated per-primitive support guarantees through a compound relational query and abstaining when a compound-level error guarantee cannot be maintained.

This should not be implemented until E02 identifies a non-saturated regime with imperfect but useful primitive recovery and genuine zero-shot query reuse.

## Revised sequence

```text
E00    synthetic machinery and failure controls
E01    historical saturated score-fusion positive control
E01-A  external-review audit and erratum
E02    factorisation sufficiency and query-algebra boundary
E03    primitive-support calibration
E04    compound uncertainty propagation and refusal
E05    limited real frozen-representation pilot
E06    real-domain query execution
E07    real-domain certified refusal
```

The first real domain remains undecided. Chess and code are leading candidates; the choice should be made through a short evidence-based domain comparison rather than intuition.

## Immediate PR sequence

1. External-review audit and blog record.
2. Evidence-contract repair.
3. Documentation-only frozen E02 contract.
4. E02 implementation.
5. E02 evidence and decision.
6. E03 support-certificate contract only if E02 identifies a meaningful operating regime.
