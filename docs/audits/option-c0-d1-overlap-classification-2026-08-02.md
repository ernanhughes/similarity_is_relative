# Option C0-D1.1 Overlap Classification

- Status: `D1_1_CLASSIFICATION_COMPLETE`
- Audit context SHA-256: `49fe499ecf5d16293a52e716ceaf88f75e256e8583b6497b934a3d884c8fd265`
- Overall outcome: `D1_CLASSIFICATION_INCONCLUSIVE`
- Next allowed action: `FREEZE_FAMILY_CONNECTED_REALLOCATION_PROTOCOL`

## Exact Pair

- Classification: `POSSIBLE_RELATED_REPOSITORY_FAMILY_LEAKAGE`
- Same source code: `false`
- Same normalized AST: `true`
- Same owner: `true`
- Token-count difference: `1`

Same GitHub owner is evidence of possible repository-family relation, not by itself proof of code leakage.

## Owner-Level Role Crossings

- Owners in more than one role: `539`
- Owners spanning c0_fit and c0_iteration: `168`
- Owners spanning three or four roles: `96`

## Near-Pair Summary

- Hamming-distance histogram: `{'0': 38, '1': 1, '2': 4, '3': 10}`
- Same-owner pairs: `3`
- Different-owner pairs: `50`
- Connected components: `33`
- Maximum component size: `8`

SimHash-near pairs are heuristic candidates, not demonstrated duplication.

## Materiality

repository-level independence passed the exact-code check, but family-level independence remains unresolved; a family identity rule must be frozen before deciding whether reallocation is required

## Firewall

- C0 selection row contents accessed: `false`
- C1 reserve row contents accessed: `false`
- Scientific result observed: `false`
- Mechanism result observed: `false`
