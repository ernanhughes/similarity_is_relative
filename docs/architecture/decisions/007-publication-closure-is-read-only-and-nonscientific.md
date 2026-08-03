# ADR 007: Publication Closure Is Read-Only And Nonscientific

## Status

Accepted.

## Context

Stage 2K can create one exact authorized canonical publication and noncanonical
audit evidence. A separate review boundary is needed to classify what happened
without retrying, repairing or reinterpreting the publication attempt.

## Decision

Stage 2L performs read-only publication evidence review and closure. It never
executes publication, retries publication, creates a missing canonical
destination, repairs audit evidence, deletes a canonical artifact, replaces a
canonical artifact or normalizes canonical bytes.

Closure is not scientific approval. Completed, failed-before-canonical,
canonical-created/audit-failed and incomplete terminal states remain distinct.
Exact candidate-byte equality is required whenever a canonical destination
exists. A canonical-created/audit-failed attempt is acknowledged as partial
success and is not relabelled as completed publication.

Closure dispositions do not authorize retry, overwrite, replacement,
materiality, allocation changes, reallocation, model refit, C0 replay,
protected-row access or D2.

## Consequences

The Stage 2 publication chain can be formally closed without any further
canonical mutation or downstream scientific action. Future materiality or
allocation work requires a separately named scientific-governance stage and
explicit human authorization.
