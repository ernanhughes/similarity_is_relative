# Similarity Is Relative

Research into whether frozen representations contain useful relational signals that their default similarity geometry fails to expose—and whether those signals can be composed, verified, and rejected when unsupported.

This repository is intentionally evidence-first. Research claims begin as falsifiable questions, become executable contracts, and are promoted to findings only after a committed verifier accepts a hash-addressed result artifact.

## Publication rule

Every sentence beginning with **“we found”**, **“RELATE improves”**, **“the embedding contains”**, or **“the operator supports”** must map to:

1. a row in [`CLAIMS.md`](CLAIMS.md);
2. a committed reproduction command;
3. a committed compact result record;
4. the hashes of the local evidence-bearing artifacts;
5. a declared falsification or revision condition.

Large datasets, embeddings, checkpoints, distance matrices and raw run outputs may remain local. Their identities, production contracts, verification results and cryptographic hashes must be committed.

## Research sequence

```text
E00 synthetic recoverability
→ E01 QM9 scalar-collapse gate
→ E02 conditional-similarity replication
→ E03 protein benchmark construction
→ E04 protein primitive relations
→ E05 unseen relational composition
→ E06 certified abstention
→ E07 sentence-embedding transfer
→ E08 long-context transfer
```

The first experiment is [`E00: Synthetic Recoverability`](docs/experiments/00-synthetic-recoverability.md).

## Current status

- Research question: **frozen**
- Claims ledger: **initialised**
- E00.1 baseline machinery: **verified**
- E00.2 operator point estimates: **verified**
- E00.3 nulls, uncertainty and certification: **pending**
- Promoted empirical findings: **none**

<!-- RELATE:E00:CHECKPOINT:START -->
## E00 checkpoints

### Baseline checkpoint

- Checkpoint: **`e00-baseline-checkpoint-v1`**
- Local artifact verification: **PASS**
- Verified regimes / metric sets: **6 / 6**
- Manifest: **`8558e1847918b08eb0db9ce512c4bcfb4e94e4a1f7dc4a222cdd2b99cd2c6220`**
- Public record: [`docs/results/e00-baseline-checkpoint-v1.md`](docs/results/e00-baseline-checkpoint-v1.md)

### Operator-matrix checkpoint

- Checkpoint: **`e00-operator-matrix-checkpoint-v1`**
- Independent verification: **PASS**
- Verified regimes / method sets: **6 / 40**
- Source manifest: **`8558e1847918b08eb0db9ce512c4bcfb4e94e4a1f7dc4a222cdd2b99cd2c6220`**
- Operator matrix: **`c25202e5842b79073ae27ab2edb5068a12846a57bcaa47cfc8d3be30436ce235`**
- Public record: [`docs/results/e00-operator-matrix-checkpoint-v1.md`](docs/results/e00-operator-matrix-checkpoint-v1.md)
- Scientific claim promotion: **blocked**

The point estimates show a strong provisional axis/rotation contrast: diagonal weighting succeeds on the axis-aligned signal and degrades after rotation, while a learned rank-one direction remains strong. E00 remains incomplete until permutation nulls, confidence intervals, confirmatory seeds and certification are verified.
<!-- RELATE:E00:CHECKPOINT:END -->

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

PowerShell entry points live under [`scripts/`](scripts/README.md).
