# Viva presentation

## Purpose

This directory contains the evidence notes and final interactive presentation
for the Granite Lifeline viva. The presentation is designed for a ten-minute
team delivery followed by questions.

The narrative begins with the vehicle-owner problem, introduces the four-layer
architecture, and then explains three connected challenges:

1. working with OBD-II journeys that have no verified fault labels;
2. using TTM and rule-based evidence to identify unusual behaviour;
3. turning that evidence into an understandable report without presenting an
   anomaly as a confirmed mechanical fault.

Evaluation, the live Dashboard demonstration, conclusions and future work
follow these challenges. Speaker handovers connect the Data, Model, Report and
Dashboard contributions without repeating the architecture explanation.

## Files

- `outline.md` records the planned narrative, speakers and timing.
- `data_challenge.md`, `model_challenge.md` and `report_challenge.md` retain the
  supporting technical notes for the three challenge sections.
- `slides/index.html` is the interactive presentation used for delivery.
- `slides/assets/` contains the presentation images and screenshots.
- `evidence/` contains saved inputs and outputs used by slide examples.

The slide deck is the delivery source of truth. The challenge Markdown files
contain supporting material and may include earlier drafting notes that do not
appear in the final presentation.

## Running locally

From `docs/viva/slides/`, serve the files over HTTP and open the local address
in a browser. For example:

```bash
python3 -m http.server 8765
```

Then open `http://127.0.0.1:8765`. The presentation supports direct slide
navigation through its on-screen controls and keyboard input.
