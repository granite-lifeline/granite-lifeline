# Manual review of the regenerated RAG ablation

This review covers the 20 reports regenerated on 1 September 2026 after the
GL-446 Report Layer fixes. Each report was checked against its saved input
context, retrieved knowledge, Validator result and automatic audit. The full
labels and case-specific evidence are in
`final_rag_multidimensional_review.json`.

## Cooling degradation — Low risk

All four reports retained the low-temperature evidence and Low-risk timing.
The controlled report did not invent a cause. The relevance gate withheld
overheating material, and the two action conditions kept technical checks with
a mechanic. The earlier unrelated pedal stopping condition is absent.

## Air-intake mass-airflow anomaly — Low risk

The reports expand mass airflow (MAF) on first use and do not expose PID as an
unexplained field. Retrieved knowledge adds contamination and calibration
possibilities with uncertainty. These explanations remain relatively long,
and the normal displayed signals cannot distinguish among the possible causes.

## Accelerator-pedal sensor — Medium risk

The reports state that the displayed signals are within their reference ranges
without claiming that the whole sensor or system operates normally. Retrieved
heat, wiring and connector causes remain possible rather than confirmed.
Owner observations and stopping conditions are specific to pedal response,
while wiring and voltage checks are assigned to a mechanic.

## Intake-air-temperature sensor flag — High risk

The reports describe a rule-based diagnostic flag and explicitly state that
the displayed temperature signals are normal. They do not expose the internal
confidence percentage or describe the flag as a confirmed fault. Retrieved
circuit and connector possibilities are category-relevant but cannot be
distinguished from the current displayed signals, so professional verification
remains necessary.

## MAP load-signal plausibility flag — High risk

All four reports preserve current High risk without describing a future
crossing into High risk. Retrieved contamination, electrical and physical
possibilities remain uncertain. Owner actions are observational, while MAP
signal and component checks are assigned to a mechanic. Internal proxy
provenance is converted into owner-facing diagnostic wording.

## Decision supported by the review

All 20 outputs were released without fallback and retained the owner/mechanic
action boundary. The earlier four manual-review defects are no longer present.
The review also shows why release compliance and mechanical accuracy must stay
separate: several retrieved causes are relevant to the anomaly category but
cannot be selected from the displayed signals alone. Technician-verified fault
and repair cases remain necessary for mechanical evaluation.
