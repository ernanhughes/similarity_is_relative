"""Clean family-domain capability package.

Stage 2A extraction from relate.experiments.option_c0_family_connected_protocol.

Modules
-------
models       Pure immutable dataclasses.
rules        Frozen edge-rule taxonomy and rule-derived constants.
repositories Repository identity, normalization and allocation-domain operations.
sources      Source-evidence construction and validation.
edges        Edge, candidate and review construction and validation.

Dependency direction
--------------------
relate.family
    -> relate.evidence  (neutral helpers)
    internally: edges -> sources -> repositories -> models
                rules -> models

The historical protocol module imports from relate.family; relate.family never
imports from relate.experiments.
"""

from __future__ import annotations
