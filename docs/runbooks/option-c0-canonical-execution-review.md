# Option C0 Canonical Execution Review

Stage 2I reviews staged canonical-input execution evidence. It does not run
the family workflow and does not publish a canonical result.

## Inputs

The review command requires exact files for:

- v2 canonical execution request;
- v2 canonical execution authorization;
- authorization/rehearsal review packet;
- prepared evidence bundle;
- authorized work directory.

The work directory must be the exact noncanonical staging directory authorized
by the request.

## Terminal States

Valid completed evidence contains claim, trace, completed receipt, review
packet, and store.

Valid blocked evidence contains claim, trace, and blocked receipt. It must not
contain a review packet or failure record.

Valid failed evidence after claim persistence contains claim, failure record,
and trace. It must not contain a receipt or review packet.

Valid failed evidence before claim persistence contains failure record and
trace, and may omit claim and store. The work directory itself proves the
authorization was consumed.

## Scientific Equivalence

Completed execution packets are compared to the authorized rehearsal packet by
a bounded scientific-payload commitment. Run-specific fields such as run ID and
workflow run identity are excluded. Scientific and safety-relevant fields,
including bounded outcome, role analysis, materiality inputs, evidence-bundle
commitment, firewall declarations, non-conclusions, and downstream decision
states are included.

A mismatch is an execution-integrity failure, not a materiality or
contamination conclusion.

## Disposition

An execution-review disposition can accept eligible completed evidence for a
later publication-authorization review or withhold execution evidence. It does
not authorize canonical publication, materiality, allocation changes,
reallocation, model refit, C0 replay, protected-row access, or D2.

## Bundle

The review bundle is immutable and noncanonical. It contains the execution
review report, the human execution-review disposition, and commitments over
both. The writer rejects destinations under `artifacts/canonical` and refuses
overwrite.
