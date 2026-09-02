# Ground Knowledge Index

## Purpose

This directory stores grounded domain knowledge used by the project.

The purpose is to document assumptions, feature definitions, rule-based
anomaly evidence and supporting references in a structured and traceable way.

This knowledge is intended to support:

* data cleaning and preprocessing
* feature engineering
* rule-based anomaly definition
* model input preparation
* report generation and explanation


## Structure

* `grounded_knowledge.yaml`
  Structured knowledge definitions for signals, features, rule-based anomaly
  evidence and thresholds.

* `reference.md`
  Supporting rationale, exploratory findings, engineering explanation, and literature references.

* `README.md`
  Navigation and maintenance guidance for this directory.


## Ownership

* Data Layer owns signal definitions and feature grounding.
* Model Layer consumes features and proxy definitions.
* Report Layer consumes the reviewed explanatory and action material.

Cross-layer changes should be synchronised before merging.


## Update Rules

When adding or modifying content:

1. Update supporting evidence in `reference.md`.
2. Update structured entries in `grounded_knowledge.yaml`.
3. Keep naming consistent with interface definitions.
4. Mark assumptions explicitly if not validated.
5. Avoid storing duplicated values across files.


## Status

`grounded_knowledge.yaml` is shared research documentation. The production
Report Layer index is built from its `report_layer` entries by
`report_layer/rag/knowledge_indexer.py`. Runtime anomaly names and interfaces
remain authoritative in `shared/anomaly_mapping.py` and `docs/INTERFACE.md`.


