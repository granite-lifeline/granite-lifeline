# Provenance — Report Challenge (Stage 3) worked example

Single running example used across index.html stages 0/1/3/4/5/6: the
committed illustrative fixture at
`model_layer/ttm-related/outputs/kit_residual_sample.json`
(cooling_degradation, Medium, risk_score 0.585, prediction_confidence
0.6534, coolant_temp 98°C vs 90–95°C reference, estimated_cycles_to_failure
4, estimated_failure_probability 1.0 — note in the source file: this
projection is illustrative, generated from a synthetic rising-risk-history
estimator demonstration, not a real vehicle lifetime prediction).

- Branch: `gl-406-viva-slides-polish-0-1`
- Commit at time of these runs: `492701da11844452787f115b9cb7fec4a197adcb`
- Date: 2026-08-04
- Model: `granite4.1:8b` via local Ollama (`http://localhost:11434`)
- Temperature/seed: not pinned — these are the pipeline's real defaults
  (`report_layer/pipeline/report_generator.py::call_ollama`); re-running
  may produce different exact wording, though the numeric-grounding
  fix is structural (prompt-rule based), not sampling-based.

## Files

| File | What it is | How it was produced |
|---|---|---|
| `01-model-input.json` | Real Model Layer input, identical to `kit_residual_sample.json` | copied, not generated |
| `02-retrieval-result.json` | Real ChromaDB retrieval for `cooling_degradation` / `medium` | `report_layer.rag.rag_retriever.retrieve_all("cooling_degradation", "medium")` — no Ollama involved |
| `03-llm-no-rag-output.json` | Real 3-layer generation with retrieval swapped for the code's own RAG-unavailable fallback text | manual layer-by-layer call using `report_generator.render_prompt`/`call_ollama`/`extract_json`, `fault_knowledge`/`actions_knowledge` = `FALLBACK_DESCRIPTION`/`FALLBACK_ACTIONS` from `rag_retriever.py` |
| `04-rag-llm-output-BEFORE-fix-BUGGY.json` | Real full-RAG generation, **before** the prompt fix below | `report_generator.generate_report(model_output)` |
| `05-rag-llm-output-after-fix.json` | Real full-RAG generation, **after** the prompt fix below, same input | `report_generator.generate_report(model_output)` |
| `06-diagnostic-no-examples-test.json` | Diagnostic-only: layer 1 with the Examples block stripped **in-memory only** (file on disk untouched) | used to isolate the root cause before deciding on a fix |

Note: the stage-1 "pure retrieval + fixed template" text ("Cooling
degradation detected. Inspect the cooling system.") is a hand-written
illustrative template, not LLM-generated — that is the entire point of
that stage (a fixed rule-based path has no generation step to run).

## Bug found and fixed

`report_layer/prompts/layer1_description.txt` contained a few-shot
example for an unrelated scenario (`accelerator_pedal_sensor`, Medium
risk) using the illustrative number `0.31%`. Granite copied that
literal number into unrelated `cooling_degradation` generations
instead of the real input's `estimated_failure_probability: 1.0`.
Confirmed root cause via `06-diagnostic-no-examples-test.json`
(removing the examples entirely also removed the leak, but regressed
tone and introduced a stronger overclaim — "until failure" — so
examples were kept and two guardrail notes were added instead).

Fix (diff against the version in this session's starting commit):

```diff
--- a/report_layer/prompts/layer1_description.txt
+++ b/report_layer/prompts/layer1_description.txt
@@ -46,6 +46,12 @@ Rules:
 - Do not convert failure probability into odds or per-trip language.
   For example, do not write "1 in 322 trips" or similar conversions.
   Preserve the model-provided percentage and horizon.
+- The numbers shown in the Examples section below (such as "56%" or
+  "0.31%") belong only to those example scenarios. They are not real
+  values and must never appear in your output. Always take
+  risk_score, estimated_failure_probability, and
+  estimated_cycles_to_failure only from the Input context above,
+  never from an example.
 - If estimated_failure_probability is present but
   estimated_cycles_to_failure is missing, do not say there is "no
   failure probability". Say no cycle estimate is available. If the
@@ -100,6 +106,10 @@ Rules:
 - If the context does not provide enough evidence, explain that clearly instead of writing "N/A".
 
 Examples:
+(Study these only for tone, structure, and plain-language style. Every
+number in them — risk scores, percentages, cycle counts — belongs to
+that example's own made-up scenario. Copy none of these numbers into
+your output under any circumstances.)
 
 Bad example (cooling_degradation, High risk):
 "The coolant_temp signal shows 102°C which exceeds the
```

Verified by rerunning the full pipeline on the identical input
post-fix: `05-rag-llm-output-after-fix.json` correctly shows
`100%` / `4 drive cycles`, with no regression in hedging or
confirmed-fault language.

## Reproduce

```bash
# retrieval only, no Ollama needed
uv run python -c "
from report_layer.rag.rag_retriever import retrieve_all
print(retrieve_all('cooling_degradation', 'medium'))"

# full pipeline, needs local Ollama with granite4.1:8b running
uv run python -c "
import json
from report_layer.pipeline.report_generator import generate_report
model_output = json.load(open('model_layer/ttm-related/outputs/kit_residual_sample.json'))
print(json.dumps(generate_report(model_output), indent=2))"
```
