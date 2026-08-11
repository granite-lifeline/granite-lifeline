# Screenshot Stimulus Manifest

**Study version:** 3.0 — 2026-08-11  
**Source:** `granite-lifeline` `develop` @
`74e58d075a10a50a9c1f01d57e5d52adfed6e346`  
**Theme:** light  
**Base capture viewport:** 1440 × 1000 CSS pixels; continuous page regions
retain the 1440-pixel desktop width and expand only the visible height.

The seven dashboard PNG files in this directory are controlled stimuli for
questionnaire version 3.0. Regenerate them using
`../screenshot_capture_plan.md`; do not edit their dashboard content manually.

Change-control check on 2026-08-10: comparing the pinned build with
`origin/develop` at `53e9088` found no changes under `dashboard/`, to
`docs/INTERFACE.md`, or to the dashboard fixture. The pinned capture set was
therefore retained.

| File | Form section | Pixel dimensions | SHA-256 |
| --- | --- | --- | --- |
| `01-demo-entry.png` | Starting with sample results | 1440 × 863 | `8b7be25f227166c4d2a8555292e827d84eb3ed780f0355b7c106a0a493eed8ea` |
| `02-three-file-message.png` | Upload and local setup | 1440 × 1000 | `2016613586e3f2073f8b222fe3fcebd29180818027ff83c674f0a2f2a772314e` |
| `03-local-run-guide.png` | Upload and local setup | 1440 × 1602 | `4f48c9d20a71730d7861ea5b421f46a4d1111582417d0ec890032f0d38bfd921` |
| `04-vehicle-overview.png` | Vehicle-health overview | 1440 × 1147 | `2561ef5f4e73e4fe1e584741c6ceacdf577b77bc5c7d12adcc362b85280c1d0e` |
| `05-cooling-risk.png` | Cooling risk and trend | 1440 × 1000 | `a8113e3f3c50cde6d566f4bba0259aa40a1423fb595bbbd914810f8a68f29f57` |
| `06-cooling-explanation.png` | Cooling explanation and action | 1440 × 715 | `4122284d0cc2b8987a1e7cfd96b196bbd8958f6eb0bba12ab626d9808960f7b8` |
| `07-export-defaults.png` | Exporting the report | 1440 × 364 | `17101f3db8c6d99511762ecdc84ca0ad2d465909b4a91d63505df6a3024de774` |

If any PNG is recaptured, update its dimensions and SHA-256 here before the
Forms are published.

## Report-pair manifest

No report PDFs or report-page PNGs are approved or captured in this version.
Do not build the revised Forms until every field below has been completed from
the Report group's controlled handoff and the pair passes
`../screenshot_capture_plan.md` §4A.

| Field | Retrieved-grounding report | No-retrieval report |
| --- | --- | --- |
| Source branch | | |
| Full source commit | | |
| Common model-input fixture | | |
| Generation date and configuration | | |
| Original PDF SHA-256 | | |
| Page count | | |
| Dashboard fixture relationship | | |

| File | Condition | Page | Pixel dimensions | SHA-256 |
| --- | --- | ---: | --- | --- |
| `reports/rag/page-01.png` | RAG | 1 | | |
| `reports/baseline/page-01.png` | baseline | 1 | | |

Extend the table for every page, retaining identical zero-padded page numbers
for the two conditions. The paths and condition labels are administration-only;
participants see only neutral Report A and Report B labels.
