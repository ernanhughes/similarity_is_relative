# ADR 006: Canonical Publication Is One-Shot And No-Replace

## Status

Accepted.

## Context

Stage 2J can authorize review of one exact canonical publication candidate and
destination, but its v1 records remain nonexecutable. The first executable
canonical publication boundary needs a separate source-bound contract and a
publication primitive that cannot overwrite or replace existing canonical
artifacts.

## Decision

Stage 2K requires a new v2 executable request and a new v2 human
authorization. The v2 request binds the Stage 2J request and authorization,
candidate logical commitment, candidate file SHA-256, execution-review bundle
identity, exact canonical destination, exact canonical parent, exact
noncanonical audit work directory, publisher source identity and continuing
prohibitions.

The payload policy is exact-byte publication: the canonical destination must be
created with the authorized candidate file bytes, and the destination SHA-256
must equal the authorized candidate file SHA-256. The executor does not
reserialize or wrap the candidate.

Canonical creation uses an exclusive no-replace byte writer based on a
same-directory temporary file and hard link creation. No overwrite, replacement
or directory-wide publication authority exists.

The audit directory is the one-shot claim. Once it is created, the
authorization is consumed. If canonical creation succeeds but audit
finalization fails, the canonical file is not rolled back; the failure record
must truthfully report that the canonical file was created and bind its SHA.

## Consequences

Replay is rejected by the existing audit directory and by the existing
canonical destination. Stage 2K publication does not determine materiality,
conclude material contamination, change allocation, authorize reallocation,
refit models, replay C0, access protected rows or start D2.
