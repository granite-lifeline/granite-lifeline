# Blind Report Layer A/B stimuli

This directory holds a within-input comparison for user testing. Five named
Seat Leon CSV trips are processed together by Data Layer, then once by Model
Layer. The saved Model output is used for both report conditions.

Participants see neutral labels **Report A** and **Report B**. They are not
told which report uses retrieval. The administrator-only key records the
condition mapping. The study must describe the source as recorded OBD-II data,
but must not describe the detected patterns as technician-confirmed faults.

The RAG condition retrieves diagnostic knowledge before report generation.
However, the three-layer prompt design keeps retrieved knowledge out of the
observation summary (`What happened?`), which must describe only the supplied
Model evidence. Retrieval is used where external diagnostic knowledge is
actually relevant: the possible-cause explanation and the owner/mechanic
actions. Holding the observation summary fixed prevents a changed description
of the vehicle data from confounding the comparison, while the report never
announces which condition used retrieval.
