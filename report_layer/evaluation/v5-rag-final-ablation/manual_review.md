# Manual review of the regenerated RAG ablation

This review covers the 20 reports regenerated on 1 September 2026. Each report
was checked against its saved input context, retrieved knowledge, Validator
result and automatic audit. The full labels and case-specific evidence are in
`final_rag_multidimensional_review.json`.

## Cooling degradation — Low risk

The controlled report preserved the low-temperature evidence and did not name
a cause. The relevance gate correctly withheld overheating material from the
three retrieval conditions. Current full RAG produced suitable Low-risk owner
and mechanic actions. Owner-safe RAG remained safe, but added an unrelated
pedal-response stopping condition and exposed the mass-airflow integral in the
mechanic request without explaining why it mattered.

## Air-intake MAF anomaly — Low risk

Retrieved knowledge added plausible contamination, connector and degradation
possibilities while retaining uncertainty. Both action conditions assigned
scan-tool work to a mechanic. All four descriptions nevertheless used `MAF`
without expanding it for the intended non-technical reader; the action
conditions also retained dense `PID` and rpm terminology in the mechanic item.

## Accelerator-pedal sensor — Medium risk

All four reports preserved Medium-risk service timing and used safe owner
actions. The shared description said that the system was operating normally,
although the input only established that the listed signals were within their
ranges. Retrieved heat, wiring and connector causes were category-relevant,
but the cause-only output connected heat near the firewall and possible
limp-home behaviour only weakly to the current evidence.

## Intake-air-temperature sensor fault — High risk

The regenerated reports no longer describe a future crossing into High risk.
All action conditions assign technical checks to a mechanic. However, the
shared description calls the result a high-risk fault and strongly suggests a
sensor issue even though all displayed signals are normal and the detection
came from rule-based evidence. Retrieved circuit and connector causes fit the
category but cannot be distinguished by the displayed signals. The retrieved
conditions also expose `rule-based proxy evidence`, which is not suitable
owner-facing language.

## MAP load-signal plausibility fault — High risk

All four reports preserved the abnormal manifold-pressure range, current High
risk and the need for professional verification without exposing a future
High-threshold projection. Cause knowledge was relevant, although the
cause-only report listed several generic alternatives that the available
evidence could not distinguish. Both action conditions kept observation with
the owner and assigned sensor, electrical and intake-leak checks to a mechanic.

## Decision supported by the review

The regenerated reports support the production owner/mechanic action boundary:
all 20 released outputs kept technical work with a professional. Retrieved
knowledge improved specificity, but did not by itself ensure that every cause
was strongly connected to the current signal direction or that every term was
plain enough for the intended reader. The remaining priorities are therefore
to revise the shared IAT and Accelerator Pedal descriptions, expand MAF and
PID, and prevent unrelated stopping conditions from entering a component
report. Mechanical accuracy remains outside this review because the fixtures
do not contain technician-verified faults or repair outcomes.
