# Ground Knowledge Index

## Purpose

This directory stores grounded domain knowledge used by the project.

The purpose is to document assumptions, feature definitions, proxy failure logic, and supporting references in a structured and traceable way.

This knowledge is intended to support:

* data cleaning and preprocessing
* feature engineering
* proxy failure definition
* model input preparation
* report generation and explanation


## Structure

Describe the responsibility of each file.

* `grounded_knowledge.yaml`
  Structured knowledge definitions for signals, features, proxy failures, and thresholds.

* `reference.md`
  Supporting rationale, exploratory findings, engineering explanation, and literature references.

* `README.md`
  Navigation and maintenance guidance for this directory.


## Ownership

Document which group is responsible for maintaining each type of knowledge.

* Data Layer owns signal definitions and feature grounding.
* Model Layer consumes features and proxy definitions.
* Report Layer consumes structured outputs and explanations.

Cross-layer changes should be synchronised before merging.


## Update Rules

When adding or modifying content:

1. Update supporting evidence in `reference.md`.
2. Update structured entries in `grounded_knowledge.yaml`.
3. Keep naming consistent with interface definitions.
4. Mark assumptions explicitly if not validated.
5. Avoid storing duplicated values across files.


## Version Notes

Record major changes to knowledge definitions.

* v0.1 → basic frame
* v0.2 → initial signal and feature grounding
* v0.3 → proxy failure definitions aligned



