# ADR 305: Live Report Validation and Correction Loop

## Status

Accepted

## Date

2026-08-10

## Context

The production report pipeline already validated the three generated report
fields, but validation happened only after all three calls. A layer scoring
below `0.8` caused the complete report to fall back to empty generated fields.
This prevented clearly poor text from reaching the dashboard, but it did not
use the validator feedback to repair a correctable wording or structure issue.

Blindly repeating the same prompt is not useful because production generation
uses temperature zero and has been observed to be deterministic. A correction
must change the prompt and tell the model exactly which checks failed.

## Decision

Each report layer now follows the same live sequence:

1. Generate the layer with its grounded production prompt.
2. Apply the existing owner-facing cleanup.
3. Validate that layer before generating the next one.
4. If its score is below `0.8`, make one new call containing the original
   grounded task, the current JSON output, and the validator warnings.
5. Re-clean and revalidate the corrected output.
6. Continue only when the corrected score is at least `0.8`; otherwise use the
   existing empty-report fallback while preserving the original risk evidence.

The correction prompt explicitly forbids adding any diagnosis, measurement,
cause, or action absent from the original grounded task. A corrected Layer 1
is therefore used to generate Layer 2, and a corrected Layer 2 is used to
generate Layer 3. The complete chain is validated again before delivery as a
final defence-in-depth check.

Technical request, timeout, HTTP, and JSON parsing failures remain separate
from semantic correction. They retain the existing maximum of three retries.
Semantic correction is limited to one attempt so a report cannot enter an
unbounded generation loop.

## Consequences

### Positive

- Correctable report-quality failures no longer discard the whole report
  immediately.
- Validator feedback changes the retry prompt, so deterministic generation can
  produce a meaningfully revised response.
- A downstream layer never receives a known below-threshold upstream result.
- The existing fail-closed dashboard behaviour remains intact when correction
  cannot produce an acceptable result.

### Negative

- A correction adds one model call and therefore latency when a layer fails.
- The validator is intentionally bounded by its explicit checks and phrase
  lists. Passing it is not proof that every sentence is mechanically correct.
- Without labelled reports from real vehicle failures and expert adjudication,
  the system cannot measure real-world diagnostic recall or guarantee detection
  of every unsupported semantic claim. This is the remaining evidence limit,
  rather than an unwired implementation step.

## Verification

`tests/test_report_generator.py` covers successful correction, use of corrected
upstream content by the next layer, safe fallback after a failed correction,
and the exact `0.8` threshold boundary.
