# ADR 001: Organize RELATE by Capability, Not Experiment Chronology

Date: 2026-08-03

Status: proposed for adoption by the architecture-reset foundation PR.

## Context

RELATE evolved through E00, E01, Option B and Option C0. Each stage added experiment-specific runners, identities, recovery tools, verifiers and corrective entrypoints. That organization made it easy to preserve the exact implementation history of each experiment, but it also made experiment names the primary software boundaries.

The active package now contains reusable responsibilities inside modules named after historical stages. Newer workflows import older experiment modules for records, embeddings, data reconstruction and model code. Corrections are layered by replacing module globals at runtime.

This structure has become an obstacle to understanding scientific failures. A defect may originate in data allocation, representation, model selection, conformal support, evaluation, evidence publication or orchestration, but those responsibilities are often combined inside a single experiment runner.

## Decision

RELATE will organize new production-style code by stable capability.

The intended top-level capabilities are:

```text
domain
data
representations
models
support
evaluation
family
evidence
workflows
cli
```

Historical experiment modules remain available during migration as compatibility facades and reproducibility references.

## Dependency direction

```text
cli
  -> workflows
      -> domain/data/representations/models/support/evaluation/family
          -> evidence
```

Additional constraints:

- clean capability packages must not import `relate.experiments`;
- workflows may compose capabilities but should not implement them;
- CLIs should contain argument parsing and invocation only;
- evidence infrastructure must be experiment-neutral;
- compatibility facades may import clean packages;
- runtime monkey-patching is prohibited in new architecture.

## Why not organize by experiment?

Experiment names describe when and why code was introduced, not what the code does.

For example, CodeBERT embedding, repository allocation, canonical hashing, Ridge primitive probes and risk-coverage evaluation may be used by several experiments. Housing them under one historical experiment creates accidental ownership and encourages later experiments to import internal implementation details.

Capability packages allow the scientific question to change without requiring another parallel implementation stack.

## Why preserve experiment modules at all?

The historical modules are part of the provenance of published and audited artifacts. Immediate deletion or rewriting would make it harder to understand exactly what produced those results.

They will therefore be retained until one of these conditions is met:

- the module is a thin compatibility facade over a clean implementation;
- its historical execution is fully represented by immutable source manifests and it has no active caller;
- an explicit legacy-retirement PR documents why removal does not damage reproduction or interpretation.

## Consequences

### Positive

- scientific mechanisms become inspectable independently;
- data, model, support and evaluation defects can be isolated;
- shared infrastructure stops being copied;
- workflows become explicit and testable;
- the canonical family runner can be implemented from coherent components;
- future experiments can reuse capabilities without importing historical runners.

### Negative

- migration will temporarily create both historical and clean paths;
- exact compatibility may require adapters;
- some old tests cannot be reused directly because they assert historical module boundaries;
- source identities for future executions will differ from historical identities;
- migration must proceed in small stages to avoid changing scientific behaviour accidentally.

## Rejected alternatives

### Rewrite the entire repository in one pass

Rejected because row order, serialization, hash identity, model behaviour and firewall rules could change together, making failures impossible to localize.

### Keep the current structure and only split large files

Rejected because smaller experiment-named files would preserve the wrong dependency direction and historical ownership.

### Move historical code directly into capability packages

Rejected as the first step because it could blur which implementation generated existing artifacts. Initial extraction should establish neutral infrastructure and explicit facades before moving scientific algorithms.

### Build the family graph runner first and clean later

Rejected because it would add another operational layer to the largest current protocol module and deepen the architecture that is already obscuring problems.

## Migration sequence

1. Quarantine historical tests.
2. Freeze the current-system map and preservation contract.
3. Extract neutral evidence infrastructure.
4. Extract the family domain and persistence layers.
5. Implement an explicit family workflow and CLI.
6. Replace the C0 wrapper chain with explicit dependency construction.
7. Extract representation, model, support and evaluation capabilities.
8. Convert or retire historical entrypoints deliberately.

## Review condition

This decision should be revisited only if capability extraction produces unavoidable circular dependencies or if a different boundary better represents stable scientific responsibilities. Convenience for one experiment is not sufficient reason to reverse it.
