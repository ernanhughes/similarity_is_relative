# Option B Domain Selection — Real Code

Date: 2026-08-01

## Decision

Option B will use:

```text
domain: real Python functions
source: CodeSearchNet Python partition
representation: microsoft/codebert-base
primitive source: Python AST
primary query: joint similarity in cyclomatic complexity,
               maximum control nesting depth,
               and distinct call-site count
```

This decision is frozen before implementation and before any CodeBERT embedding or test metric is generated.

## Why code

Code is selected over chess, molecules and language for the first premise test because it satisfies all required constraints within the ten-working-day budget:

- real artifacts created outside the project;
- an established frozen representation trained outside the project;
- objective primitive values extractable without human annotation;
- repository-separated public splits;
- direct manual inspection of errors;
- immediate relevance to the user's software repositories and AI-in-work objective;
- a negative result can close the programme cleanly.

## Why CodeSearchNet

CodeSearchNet provides real functions from open-source repositories and separates repositories across train, validation and test. That split is materially stronger than random function splitting because near-duplicate project conventions and same-repository implementations cannot trivially leak across partitions.

Only the Python partition is permitted. Adding another language would turn one kill test into a matrix and is outside Option B.

## Why CodeBERT

CodeBERT is an externally pretrained general-purpose code representation with a straightforward frozen embedding interface. It was trained for code and natural-language/code tasks, making raw cosine a credible competitor rather than a straw baseline.

This is important: the premise test must be able to fail because default geometry is already adequate.

GraphCodeBERT and UniXcoder are not included. A second representation would create post-result model selection and exceed the one-representation contract.

## Why these primitives

The three AST-derived primitives are:

1. cyclomatic complexity;
2. maximum control nesting depth;
3. distinct call-site count.

They were chosen because they are:

- objectively computable;
- meaningful to software structure;
- not labels planted in the representation;
- heterogeneous but simple enough to audit;
- available for every eligible Python function;
- independent of docstring quality and human annotation.

They are not claimed as novel software metrics.

## Why one Chebyshev query

The primary query asks for functions jointly similar across all three primitives. Chebyshev distance uses the worst primitive mismatch and therefore represents a clear AND-style relation without returning to E01's weighted-product-space design.

Only one query is permitted. The question is whether a real raw geometry gap exists at all, not which query form produces the largest gap.

## Why the threshold is severe

The frozen continuation threshold is:

```text
predicted primitive hard-negative triplet accuracy
- strongest raw geometry hard-negative triplet accuracy
>= 0.10
```

A smaller gap may still be statistically detectable or locally useful. It is not enough to justify the remaining RELATE programme under the post-E01 decision.

Secondary metrics must be reported, but they cannot rescue a primary gap below `0.10`.

## Prior-art boundary

Existing work already establishes:

- CodeBERT as a pretrained code representation;
- CodeSearchNet as a real repository-separated code benchmark;
- frozen probing of structural and semantic information in code models;
- linear probes and AST metrics as standard methods.

Option B does not seek novelty in any of those components. It tests only whether default embedding geometry materially underexposes one objective compound structural relation.

## Decision consequences

```text
REAL_PREMISE_FAILED
    RELATE closes.
    Publish the negative result.
    Preserve only the evidence-first methodology as a separate line.

REAL_PREMISE_SUPPORTED
    Option C becomes authorised.
    No other extension is authorised.
```

## Budget

From merge of the contract PR:

```text
maximum: 10 working days
```

The budget includes dataset preparation, embedding extraction, implementation, verification, result checkpoint and final decision.

If the experiment cannot be executed within the budget, the design must be simplified. The deadline may not be extended by adding models, languages, primitives or queries.