# Screenshot Stimulus Capture Plan

**Version 3.0 — 2026-08-11**  
**Required source build:** `granite-lifeline` `develop` @ `74e58d0`

These instructions create the controlled images referenced by
`questionnaires.md`. Participants never perform these steps. Report images
cannot be captured until the controlled handoff in `protocol.md` §4 is
complete.

## 1. Capture environment

Use the sibling main repository:

```sh
cd ../granite-lifeline
git switch develop
git status --short --branch
git rev-parse HEAD
```

Required state:

- branch: `develop`
- full commit beginning `74e58d075a10a50a9c1f01d57e5d52adfed6e346`
- no tracked working-tree changes

Start the dashboard with curated demo data available:

```sh
.venv/bin/streamlit run dashboard/app.py \
  --server.port 8502 \
  --server.headless true
```

Use one fresh private browser window at `http://localhost:8502` with:

- desktop viewport: 1440 × 1000 CSS pixels as the base layout;
- browser zoom: 100%;
- dashboard theme: light;
- no browser extensions, bookmarks, accounts, notifications, or personal
  information visible;
- no developer tools or local filesystem paths visible in the final crop.

Capture PNG, not JPEG. Crop to the application surface while retaining enough
surrounding context to show where the panel sits. Do not add arrows, boxes,
answer labels, or explanatory annotations.

For a continuous page region taller than 1000 pixels, retain the 1440-pixel
desktop width and expand only the browser's visible height to the exact region
boundary. Move the pointer to an empty corner before capture so hover states
and Plotly toolbars are not recorded.

## 2. Temporary upload files

Screenshot 2 requires the current three-file validation state. Create three
temporary `.csv` files outside both repositories with neutral names:

```text
2026-06-01-trip.csv
2026-06-02-trip.csv
2026-06-03-trip.csv
```

The three-file count is rejected before the application reads their contents,
so the temporary files must not contain project or participant data. Remove
them after capture.

## 3. Required screenshots

### 01-demo-entry.png

1. Start a fresh dashboard session.
2. Remain on the landing page; do not select files.
3. Confirm these controls are visible together:
   - `How to Run Locally`
   - CSV selection area
   - `Run Analysis`
   - `Explore with demo data`
4. Capture the application content from the Granite Lifeline header through
   the demo-data button.

**Evidence check:** a viewer can see how to enter demo results without using
the upload path.

### 02-three-file-message.png

1. Select the three neutral temporary CSV files together.
2. Confirm all three filenames are visible.
3. Click `Run Analysis`.
4. Capture the selected-file list and the complete error card.

**Required text:**

```text
Upload At Least 5 CSV Files
Failure prediction needs at least five chronological trips.
You selected 3 CSV files.
```

No model, report layer, or Ollama process should start for this state.

### 03-local-run-guide.png

1. Return to a fresh landing page.
2. Click `How to Run Locally`.
3. Capture the page title, four numbered step chips, explanatory text, and
   command cards in one continuous page image.
4. Retain `← Back to Upload` so the image has navigation context.

**Required step labels:** `Prepare project`, `Install tools`, `Start Granite`,
and `Open dashboard`.

### 04-vehicle-overview.png

1. Return to the landing page and click `Explore with demo data`.
2. Confirm the orange `Data source notice` appears.
3. Confirm the urgent-attention banner and High/Medium/Low legend appear.
4. Confirm all five cards are present and Cooling System appears first at 86%.
5. Capture from the overview title through the last component card. A
   continuous-page image is allowed.

**Required card order:** Cooling System, Air Intake, Manifold Pressure, Intake
Air Temperature, Accelerator Pedal.

### 05-cooling-risk.png

1. From the overview, click Cooling System `View Details →`.
2. Capture the component title, Failure Prediction panel, data-quality notes,
   86% gauge, and complete trend chart.

**Required visible values:** `72%`, `15 trips`, `86%`, and a trend rising from
45% to 86%.

### 06-cooling-explanation.png

1. Stay on the Cooling System detail page.
2. Scroll below the risk chart.
3. Capture the Key Signals section and all three explanation cards:
   `What's Happening`, `Why This Matters`, and `What You Should Do`.
4. Ensure every recommended action is readable.

**Required visible actions:** avoid heavy driving if safe; check coolant when
the engine is cool; ask a mechanic to inspect the cooling system promptly.

### 07-export-defaults.png

1. Click `← Back to Overview`.
2. Do not open or change export options.
3. Scroll to `Export Report`.
4. Capture the ready-to-download summary and both default download cards.

**Required visible values:** `5 component(s)`, `3 PDF section(s)`,
`5 CSV column(s)`, `Download PDF ZIP`, and `Download CSV ZIP`.

## 4A. Report-PDF stimulus capture

Use only the two final PDFs supplied through the Report group's controlled
handoff. Do not generate, edit, rewrite, or substitute report text during
capture.

### Required pre-capture checks

Confirm and record all of the following before converting a page:

- the source branch, full commit, model-input fixture, generation date, and
  generation configuration for each report;
- the condition mapping: `rag` or `baseline`;
- that risk level, risk score, failure estimate, key signals, and recommended
  actions come from the same underlying case in both reports;
- that page count, page order, headings, visual layout, and non-generated
  content are identical; and
- whether that report case is the same fixture as the dashboard screenshots.

If any check fails, stop capture and return the pair to the Report group. Do
not repair one PDF locally or use a mismatched pair.

### Conversion procedure

1. Preserve each supplied PDF unchanged in the approved university-managed
   evidence location; do not place the PDF in a participant-facing Form.
2. Render every page of each PDF at the same page size and resolution. Retain
   the full page; do not crop, stitch, reorder, or composite report pages.
3. Save the condition files under these exact directories:

   ```text
   docs/user_test/assets/reports/rag/page-01.png
   docs/user_test/assets/reports/rag/page-02.png
   docs/user_test/assets/reports/baseline/page-01.png
   docs/user_test/assets/reports/baseline/page-02.png
   ```

   Continue the zero-padded sequence through the last page. Both directories
   must contain the same number of files.
4. Open every PNG at actual size and in Google Forms desktop and phone preview.
   Page text must be readable without opening the original PDF.
5. In the `rag_first` Form, insert all `rag` pages as neutral Report A pages,
   then all `baseline` pages as neutral Report B pages. Reverse only these two
   source sets in the `baseline_first` Form.
6. Record the PDF and PNG SHA-256 hashes, dimensions, fixture, source commit,
   and condition mapping in `assets/README.md`.

Do not show `rag`, `baseline`, file paths, source branch names, or report
generation details to participants. The filenames are administration-only
evidence and are decoded only after response export.

## 5. Image processing rules

- Preserve the source pixels; resizing is allowed only once for a legible
  Google Forms crop.
- Do not sharpen, recolour, remove interface elements, or composite states
  from different sessions.
- A long page may be stitched only from overlapping captures of the same
  unchanged page state.
- Remove browser chrome if it contains machine-specific information.
- Use the exact dashboard filenames above and the report-directory filenames
  in §4A under `docs/user_test/assets/`.
- Record pixel dimensions and SHA-256 hashes in `assets/README.md`.

## 6. Capture acceptance check

Open every final PNG at actual size and confirm:

- [ ] Text used by its Google Forms question is readable.
- [ ] No image reveals the analyst answer key.
- [ ] No personal, account, path, or participant data is visible.
- [ ] The light theme and component colours are consistent.
- [ ] The seven files come from one build and one fixture.
- [ ] The values match `protocol.md` §4.
- [ ] Images remain readable in both desktop and mobile Google Forms previews.
- [ ] Every report PDF and PNG has a recorded hash, source commit, fixture,
      generation configuration, and condition mapping.
- [ ] The report-pair checks in §4A passed before either Form was built.
- [ ] Both report directories contain an identical, complete, ordered page set.
- [ ] In each Form, neutral Report A/B labels conceal the retrieval condition.
