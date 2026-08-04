# Current Test Suite

The historical test suite under `tests/` is intentionally quarantined during the RELATE architecture reset.

It is preserved as reference material but is not collected by pytest and is excluded from Ruff. Those tests encode the chronology, wrappers, implementation accidents, and module boundaries of the existing experiment-oriented repository. Requiring the new architecture to satisfy them would preserve the structure being replaced.

This directory is the collection root for tests written against the clean capability-based architecture.

## Current status

- historical tests deleted: **no**
- historical tests collected: **no**
- historical tests linted: **no**
- behavioural coverage of the reorganized system: **not yet established**
- canonical evidence or scientific artifacts changed by this quarantine: **no**

## Reintroduction rule

Tests should be added here as stable modules emerge. They should test public capability contracts rather than historical experiment file layouts or runtime monkey patches.

The old suite may be mined for invariants, fixtures, canonical identities, and failure cases, but it should not be re-enabled wholesale.
