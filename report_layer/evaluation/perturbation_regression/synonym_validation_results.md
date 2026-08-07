# Synonym Pair Validation (WordNet, lightweight — Theil et al. check)

Checks whether the hand-picked synonym pairs used in the perturbation regression tests are supported by WordNet, and specifically whether any are registered antonyms — the failure mode Theil et al. report for distributional/embedding-based synonym search (their example: "probably"/"certainly" ranked as close neighbours despite opposite polarity). No embedding model was trained or downloaded; WordNet's explicit antonym relation is used instead, which directly labels polarity rather than only giving a similarity score.

## Sanity check

| Pair | Shares synset | Path similarity | Antonym flag |
|---|---|---|---|
| probably / certainly | False | 0.33 | no |

## Our pairs

| Pair | Shares synset | Path similarity | Antonym flag |
|---|---|---|---|
| elevated / high | False | 0.33 | no |
| indicate / suggest | True | 1.00 | no |
| indicating / suggesting | True | 1.00 | no |
| malfunction / failure | False | 0.50 | no |
| inspect / check | False | 0.33 | no |
| advisable / recommended | False | — | no |
| condition / situation | False | 0.50 | no |
| sufficient / adequate | False | 0.33 | no |
| possible / potential | True | 1.00 | no |
| slight / minor | False | 0.33 | no |
| reading / measurement | False | 0.50 | no |

## Conclusion

**10 of the 11 single-word SYNONYMS pairs are comparable in WordNet, and none of those 10 are registered antonyms.** The 11th pair (advisable/recommended) is not a confirmed-clean result — WordNet found no path between any of their synsets at all (best_path_similarity=None), because "advisable" (adjective) and "recommended" (participial adjective) don't align in WordNet's part-of-speech structure. This is the method giving no verdict, not a verdict of "clean" — a structural coverage gap in the check itself, not evidence either way about whether the two words are safe synonyms. The two pairs that actually caused instability in the perturbation tests — indicate/suggest and possible/potential — are also the two strongest matches (shares_synset=True, path_similarity=1.0), i.e. WordNet's highest possible confidence that they are genuine synonyms. This confirms those two instabilities were a keyword-list coverage gap (the phrase list not including "may suggest" or "potential explanation"), not a bad synonym choice — consistent with how they were already documented, but now independently corroborated rather than just asserted.

**Honest limitation of this check itself**: the sanity-check pair (probably/certainly, Theil et al.'s own reported false match) is *not* flagged as a WordNet antonym either — WordNet does not encode an antonym relation between these two modal adverbs, so a pure antonym-relation lookup would have missed exactly the case Theil et al. reported. path_similarity for that pair (0.33) is unremarkable and does not clearly distinguish it from several of our own fine pairs at the same score (elevated/high, inspect/check, sufficient/adequate, slight/minor). This means WordNet's antonym relation is not a complete substitute for an embedding-based nearest-neighbour check for this specific failure mode — it catches strict lexical antonyms (hot/cold) but not gradable-certainty opposites (probably/certainly). A full embedding-based check remains valuable future work for exactly this reason, rather than being made redundant by this lighter check.
