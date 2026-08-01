# Similarity Is Relative

Research into whether frozen representations contain useful relational signals that their default similarity geometry fails to expose—and whether those signals can be composed, verified, and rejected when unsupported.

This repository is intentionally evidence-first. Research claims begin as falsifiable questions, become executable contracts, and are promoted to findings only after committed evidence, explicit decision rules, and an appropriately classified verification process.

## Publication rule

Every sentence beginning with **“we found”**, **“RELATE improves”**, **“the embedding contains”**, or **“the operator supports”** must map to:

1. a row in [`CLAIMS.md`](CLAIMS.md);
2. a committed reproduction command;
3. a committed compact result record;
4. the hashes of the local evidence-bearing artifacts;
5. a declared falsification or revision condition.

Large datasets, embeddings, checkpoints, distance matrices and raw run outputs may remain local. Their identities, production contracts, verification results and cryptographic hashes must be committed.

Verification language is explicit:

- **deterministic replay** means the same implementation reproduced the result tree;
- **independent recomputation** requires separate substantive metric and decision code;
- neither term alone implies that the scientific gate passed.

## Research sequence

```text
E00 synthetic recoverability
→ E00.5 nonlinear-boundary diagnosis
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
- Claims ledger: **split into evidence-bearing component claims**
- E00.1 baseline machinery: **verified**
- E00.2 operator point estimates: **verified**
- E00.3 seed-17 certification: **replay verified; scientific gate failed**
- E00.4 five-seed confirmation: **replay verified; 6 of 7 decisions matched; scientific gate failed**
- Synthetic linear recovery and basis-dependence components: **replicated across five seeds**
- Reliable nonlinear XOR recovery: **insufficient evidence**
- Complete E00 certification claim: **blocked**
- E00 evidence audit: [`docs/audits/e00-evidence-audit-2026-08-01.md`](docs/audits/e00-evidence-audit-2026-08-01.md)
- Promoted cross-domain or RELATE algorithmic findings: **none**

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
- Replay verification: **PASS**
- Verified regimes / method sets: **6 / 40**
- Source manifest: **`8558e1847918b08eb0db9ce512c4bcfb4e94e4a1f7dc4a222cdd2b99cd2c6220`**
- Operator matrix: **`c25202e5842b79073ae27ab2edb5068a12846a57bcaa47cfc8d3be30436ce235`**
- Public record: [`docs/results/e00-operator-matrix-checkpoint-v1.md`](docs/results/e00-operator-matrix-checkpoint-v1.md)
- Scientific claim promotion: **blocked**

### Seed-17 certification attempt

- Checkpoint: **`e00-certification-attempt-v1`**
- Replay verification: **PASS**
- Scientific gate: **FAIL**
- Supported decisions: **5 of 7**
- Certification: **`f095fada6527d1214c26c1086d95c751df5ebc4f267c7bd1a2c70a7ec5279b16`**
- Decision tree: **`32e084b8a7bde09d80e19c9b0df00b8f55df1cdde5db329ab74141e8a331c832`**

### Five-seed confirmation attempt

- Checkpoint: **`e00-multiseed-confirmation-attempt-v1`**
- Deterministic replay verification: **PASS**
- Scientific gate: **FAIL**
- Required decisions matched: **6 of 7**
- Aggregate result: **`8dd526eaa45a28f56c99cb1045138685b89982109dbf61fb9788a6a65937e86d`**
- Decision tree: **`25b52842a4d5fbfefa1145c8f406328dc70744659852b7aa0535cf06788f4c90`**
- Public record: [`docs/results/e00-multiseed-confirmation-attempt-v1.md`](docs/results/e00-multiseed-confirmation-attempt-v1.md)
- Audit and erratum: [`docs/audits/e00-evidence-audit-2026-08-01.md`](docs/audits/e00-evidence-audit-2026-08-01.md)
- Complete E00 claim promotion: **blocked**

The replicated synthetic result is bounded: a supervised scalar direction strongly recovered the registered linear relation in native and rotated bases, while raw cosine and Euclidean neighbourhoods exposed it poorly and diagonal coordinate weighting degraded after rotation. This is not an algorithmic advantage over ridge predicted-value retrieval; those scalar ridge geometries are ranking-equivalent in this setting.
<!-- RELATE:E00:CHECKPOINT:END -->

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

PowerShell entry points live under [`scripts/`](scripts/README.md).
