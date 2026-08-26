# Viva Script: Slides 10-14

## [Slide 10] Pipeline handoff: evidence to action

At this point, the technical pipeline has produced more than a risk score.
The data layer cleans the OBD-II history, the model identifies early risk evidence, and the report layer turns that evidence into grounded explanations.

The key transition here is that the report output becomes the dashboard input.
So the owner does not just see "something is wrong"; they can see what changed, what it may mean, and what action they should take next.

**[Flip to Slide 11]**

## [Slide 11] Dashboard journey

This slide shows the user journey in the dashboard.
First, the user can see how to run the project locally, including setup, pipeline commands, and dashboard launch commands.

**[Click / move to upload step]**

Then the user uploads an OBD-II CSV file and clicks **Run Analysis**.

**[Click Run Analysis]**

After analysis, the dashboard shows component-level risk cards.
For example, the cooling system has a high risk score, the air intake system also shows elevated risk, and missing data is clearly marked as N/A.

**[Click View Details]**

In the detail view, the dashboard combines four things: failure prediction, risk score, risk score trend, and key signals.
The diagnostic report is then organised into three owner-facing sections: what is happening, why it matters, and what the user should do.

**[Flip to Slide 12]**

## [Slide 12] Complete result

This is the final end-to-end result.
Raw OBD-II readings are cleaned and contextualised.
The model produces early risk evidence.
The report layer creates a grounded explanation.
Finally, the dashboard turns that explanation into visible owner action.

We built and ran this complete pipeline on the available Seat Leon dataset.

**[Flip to Slide 13]**

## [Slide 13] Evidence boundary

However, it is important to be clear about what we have and have not proven.
We demonstrated that the architecture runs, that healthy history can provide context, and that unexpected changes can become cautious guidance.

But we have not yet proven confirmed mechanical failure prediction, how early a real fault appears, or whether the approach generalises to other vehicles.

So our result validates the architecture, not universal fault prediction.

**[Flip to Slide 14]**

## [Slide 14] Future work

The next step is to expand carefully.
First, we need more data from the same vehicle, ideally connected to verified maintenance outcomes.
Then we can recognise and explain more types of change.
After that, we should validate across more vehicles of the same model before moving to other models.

So the principle is simple: understand one vehicle well, validate the same model, and only then generalise.

Thank you.
