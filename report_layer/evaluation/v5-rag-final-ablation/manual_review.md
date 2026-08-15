# Manual review of final-pipeline RAG ablation

This review applies the separated measures defined in `README.md`. It is a
case audit, not a statistically representative estimate: each anomaly type is
represented by one fixture.

## Cooling degradation — Low risk

- The baseline invented plausible causes from model knowledge, including fan
  behaviour and sensor drift, but those causes were not traceable to supplied
  evidence.
- Cause RAG made the explanation more component-specific, but the retrieved
  passage was excessively broad and dominated by overheating faults that did
  not match the low-temperature pattern. The production prompt's explicit
  cooling caution prevented most of this irrelevant material from entering
  the report.
- Current full RAG converted useful retrieved actions into a safe coolant-level
  check and delegated infrared measurement to a mechanic.
- Owner-safe RAG retained simple observation and explicitly warned against
  touching hot components. In this case it was safer but not clearly more
  informative than the current full condition.

## Air-intake MAF anomaly — Low risk

- All input readings were within their stated ranges, so the anomaly label and
  otherwise normal evidence required cautious interpretation.
- Cause RAG explained the mass airflow sensor and supplied traceable candidate
  causes such as contamination and connector problems.
- Current full RAG directly asked the owner to connect a scan tool, inspect a
  connector and use contact cleaner. These are technically specific but do not
  match the assumed non-technical audience.
- Owner-safe RAG redirected scanning and wiring checks to a mechanic. It also
  introduced a duplicated “or or”, showing that audience safety and language
  quality must remain separate checks.

## Accelerator-pedal sensor — Medium risk

- All listed signals were within range despite the Medium risk score. Each
  report acknowledged that immediate failure was not established.
- Cause RAG supplied component-specific alternatives such as early wear or a
  connector issue. The legacy evaluator penalised “could indicate” because its
  hedge list did not contain that phrase; this is a scoring defect rather than
  an unsafe certainty claim.
- Current full RAG asked the owner to inspect a harness connector. Owner-safe
  RAG instead assigned that check and diagnostic scanning to a mechanic while
  asking the owner only to observe warnings and pedal response.

## Intake-air-temperature sensor fault — High risk

- The input combines a High current risk with a 0.31% probability of crossing
  the High-risk threshold in the next ten trips. All four reports repeated both
  fields but failed to explain that they conflict. This is the clearest failure
  of relationship-level faithfulness in the run.
- Retrieved cause knowledge was relevant, but current action knowledge offered
  only replacement of the MAF sensor or ECM. The model did not copy those
  unsupported replacement instructions, which was desirable.
- The legacy evaluator incorrectly penalised “before treating it as a confirmed
  fault”. Owner-safe RAG improved the action role boundary by sending sensor,
  harness and scan-tool checks to a qualified mechanic.

## MAP load-signal plausibility fault — High risk

- Cause RAG explained the MAP sensor and added plausible, traceable checks for
  wiring, connectors and vacuum leaks.
- The current action passage was conditional on turbo engines and poorly
  matched to the available vehicle context. The report relied mainly on cause
  knowledge instead of copying this passage.
- Current full RAG still told the owner to check vacuum hoses. Owner-safe RAG
  assigned sensor, hose and wiring verification to a mechanic.
- As in the IAT case, all conditions failed to address the High-risk/current-
  threshold contradiction.

## Decision supported by this run

RAG should not be accepted or rejected as one indivisible feature. The evidence
supports keeping retrieval for component descriptions and possible causes,
subject to relevance filtering. It does not support passing workshop actions
directly into a prompt for non-technical owners. Action knowledge should be
structured by audience role before generation, and inconsistent upstream risk
fields should block release or trigger an explicit limitation statement.
