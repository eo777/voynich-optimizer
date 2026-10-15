# Echo7: rule-guided paths and historical information reference

15 October 2026. Completed sensitivity study; prior models remain available.

The desired chol → cheol → chedy route was already present in the scheduled graph. Initialization alone did not beat the previous achieved objective. Preserving initial ch/sh classes and adding a continuing family preference produces a much more coherent version of that route while retaining slightly more word-ID information. Its frequency mismatch is larger. These findings depend on explicit assumptions; they do not identify historical meanings or ancestry.

## What was changed

The original optimizer uses the scheduled catalogue as allowed edges. It does not weight those edges by confidence or degree, and it fits a separate routing vector for each spelling at each transition. The graph permits chol → ol and later ol → shol. BENCH_DROP_l is a Theory, but the overlapping L_NOM_L is catalogued as a Rule: simply removing tentative operators would not remove this alternative.

The established preferred route uses S1/C1.1 at 1b → 1.5a (chol → cheol), retention into 2a, and B1/C1.2 at 2a → 3a (cheol → chedy), with later retention possible. The parallel sh path preserves sh throughout. Composed C1 routes also exist. No edge was added.

1. **Initialization only:** start from the previous fitted channel, replacing plain ch/sh terminal-liquid family rows, with any retained prefix, by guesses favoring existing forward S1 early and B1/C1 later. Two guesses assign 50% or 95% to the preferred change and retain the rest; rows without such a permitted target favor identity. The e+dy results favor retention. Other rows are unchanged. These percentages are initial guesses, not measured conversion rates. The original objective remains mean section total variation + lambda × final fractional word-ID information loss. Both lambda=0.2 and 0.75 were tested. The previous feasible model remains eligible and wins both comparisons.

2. **Preserve initial classes:** every current spelling belongs to initial ch, initial sh, or other. Edges between these three classes are prohibited, closing neutral-spelling bypasses. This also prohibits initial bench deletion/attachment; it is stronger than banning direct ch/sh substitution. Internal benches in words with other initials are not separately locked. The same two guided starts, a refined projection of the earlier fit, and a frequency-optimal start are evaluated under the unchanged objective.

3. **Continuing family preference:** retain that partition and lambda=0.75, then add a routing KL penalty toward a template with 50% early S1 conversion and 95% later B1/C1 conversion; otherwise retain the family spelling. Each supported edge has 1e-6 dust before normalization. Only the selected current-word family rows incur the penalty. The expected KL in nats is averaged over transitions and divided by the fixed starting family mass. Strengths 0.03 and 0.1 are tested. This changes the objective; it cannot be called an optimization improvement under the old objective. Final refined locked candidates and the exact template remain eligible.

Every kernel is source-blind: all original values at the same current spelling follow the same probabilities. Initial token priors remain fixed. Every starting spelling, including a hapax, retains a separate ID. Searches use at most 220 L-BFGS-B iterations per start. Exact unsmoothed scores select candidates, and iteration-limit statuses are reported. No global information optimum is claimed.

## Results

| Model | lambda | Mean usage TV | Final usage TV | All-word information | Common-word information | chol → chedy | shol → shedy |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rule-guided initialization (lambda=0.75) | 0.75 | 53.02% | 53.36% | 94.00% | 91.99% | 0.00% | 70.67% |
| Rule-guided initialization (lambda=0.2) | 0.2 | 50.76% | 51.43% | 87.47% | 78.19% | 27.41% | 58.49% |
| Initial ch/sh preserved (lambda=0.75) | 0.75 | 54.62% | 56.40% | 94.97% | 92.82% | 73.85% | 79.41% |
| Initial ch/sh preserved (lambda=0.2) | 0.2 | 52.65% | 54.64% | 89.53% | 83.20% | 64.08% | 76.34% |
| Initial ch/sh preserved + family preference (0.03) | 0.75 | 58.00% | 60.69% | 94.98% | 94.02% | 80.06% | 99.75% |
| Initial ch/sh preserved + family preference (0.1) | 0.75 | 58.60% | 61.44% | 95.05% | 94.49% | 99.58% | 99.90% |

The initialization-only rows retain the previous fits, so their scores are also the baseline. At lambda=0.75 the starting fit retains 94.00% all-word and 91.99% common-word information. The strongest continuing preference retains 95.05% and 94.49%, respectively; mean TV rises from 53.02% to 58.60%. Every locked model has exactly zero opposite-initial value mass.

The original named support has a certified minimum mean TV of 50.71%; preserving the three initial classes raises this to 52.64%. These are support-specific fixed-prior frequency bounds, not thresholds for language plausibility.

Common means at least ten occurrences in 1b. Its retained-information percentage conditions on membership in that cohort; the complete files separately give uncertainty against all competing values. Strongest-prior common uncertainty against all values is 0.401618 bits, versus common initial entropy 5.056744 bits. Unattested identity persistence remains permitted: the strongest-prior final mass on observed spellings is 66.57%. That simulated persistence does not establish observed historical survival.

## Inspect the proposed path and its usage

[Open chol under the stronger continuing family preference](index.html?word=chol&condition=guided-1b-family_bias_0.1#word-explorer). All six new systems are also in the word selector.

| Section | Original chol value at chol | At cheol | At chedy | Whole-model chedy rate / 10,000 | Observed chedy rate / 10,000 |
|---|---:|---:|---:|---:|---:|
| 1b | 100.00% | 0.00% | 0.00% | 0.00 | 0.00 |
| 1.5a | 78.05% | 21.95% | 0.00% | 0.00 | 0.00 |
| 2a | 41.69% | 58.31% | 0.00% | 0.00 | 3.22 |
| 3a | 9.16% | 13.65% | 77.19% | 317.86 | 158.23 |
| 3b | 2.97% | 13.65% | 83.38% | 346.02 | 212.38 |
| 3c | 2.97% | 13.65% | 83.38% | 346.01 | 137.61 |
| 4c | 0.25% | 2.17% | 97.58% | 398.44 | 234.88 |
| 4a | 0.01% | 0.40% | 99.58% | 405.32 | 302.41 |

At 4a the stronger family preference projects chedy at 405.32/10,000 against 302.41 observed (206 tokens), and shedy at 190.66 against 361.13 observed (246 tokens). The intuitive route therefore does not exactly reproduce these endpoint frequencies. A change of usage, other donors, different conversion shares, or a different mapping would be needed; the fit alone does not decide which.

As an independent arithmetic check, merge only the bare ch liquid spellings into chedy and the bare sh liquid spellings into shedy, leaving every other initial ID distinct. That alone retains 99.1198% of all-word ID information and 97.2939% of common-only information. This is not a fitted whole-chain model. It shows that a few coherent family merges do not mathematically require the much larger losses seen under unconstrained generic mixing.

## Historical reference

The following are new measurements from existing editor-aligned manuscript forms and expansions, preserving abbreviation signs. They use the same information formula, 1 − H(full-word spelling | written form) / H(full-word spelling), without sentence context. They are measured isolated-form spelling-ID references, not published universal loss rates or decoded semantics.

| Reference | Paired tokens | Common-word information retained | Common-word information lost | Best isolated-form error | Expanded-frequency TV after majority decoding |
|---|---:|---:|---:|---:|---:|
| Vulgate Psalm 101: 48 manuscript witnesses | 15,476 | 99.96% | 0.04% | 0.14% | 0.14% |
| Dated Latin manuscripts: 101 samples | 14,268 | 99.93% | 0.07% | 0.38% | 0.36% |
| Fontenay: 104 charters | 19,551 | 99.88% | 0.12% | 0.32% | 0.28% |
| Saint-Victor Latin 14525: one hand | 10,621 | 99.73% | 0.27% | 0.89% | 0.83% |

A real example: Fontenay mͦ has editor expansions modo (9), monachus (5), monacho (1), monachi (1). Those 16 occurrences are ambiguous, but they are only 16 of 19,551 tokens. Multiple surface forms for one expanded word need not lose word identity; several expanded words sharing a surface can. Some collisions distinguish spelling variants rather than meanings.

The known channel for the same aligned tokens has essentially zero forward frequency mismatch by construction, even when collisions exist. The last table column is a different quantity: frequency distortion after always choosing one majority expansion for each surface. Finite samples can miss alternative expansions; witness pooling, normalization, partial expansion and transcription conventions matter. Witness-specific and period results, a target-quality sensitivity, all provenance and worked examples are in the [historical reference](historical_reference.html).

For a published contextual expansion result, [Camps, Vidal-Gorène and Vernet (2021), Table 4](https://arxiv.org/pdf/2107.03450) report 97.02% overall expansion accuracy and 97.92% on ambiguous inputs. These are prediction accuracies, not information-retention percentages. The paired data come from [ORIFLAMMS Psalm witnesses](https://github.com/oriflamms/PsautierIMS), [dated manuscripts](https://github.com/oriflamms/Dated-and-Datable-Manuscripts_LIRIS), [Fontenay](https://github.com/oriflamms/Fontenay-oriflamms), and [Saint-Victor](https://doi.org/10.5281/zenodo.5071964).

## What frequency mismatch can and cannot establish

A separate unchanged-language control divides 612,195 letter-word tokens from the Clementine Vulgate into 20 disjoint eight-passage chains with the exact Echo section lengths. An identity mapping preserves 100% of initial word identity, while fixed initial frequencies give 58.81% average TV and 59.03% final TV. Three shuffled full-corpus controls give 51.43% average TV. The large inflected vocabulary and finite sampling account for much of this mismatch. With individual common words plus one all-other bucket, average TV is 11.60% naturally and 3.14% shuffled; within-common renormalization instead gives 24.50% and 8.83%. Those denominators differ.

This is not a 59% acceptable threshold for Voynich: vocabulary, morphology, genre and repetition are not matched, and the 1598 Clementine recension is not a fifteenth-century scribal witness. It demonstrates that low frequency mismatch and high identity preservation are separate aims. Minimizing TV too strongly can reward implausible reassignment simply to explain normal usage variation. Historical abbreviation loss is low in these samples, whereas the fitted Voynich loss is conditional on unknown routes and fixed-usage assumptions. The earlier low scores do not establish unavoidable semantic loss.

## Verification and reproduction

Independent full-vocabulary replay verifies all six retained channels, every stage's frequency and entropy metrics, focal routes, eight reconstructed guided seeds, support and initial partitions. Maximum discrepancy 5.33e-15. The continuing-prior analytic gradient passes finite differences within 8.11e-12. Selection accounting for unselected refinement candidates is retained, but their intermediate kernels are not stored. Browser export independently checks 56 transition replays within 6.66e-16.

Run rule_guided_optimization.py, refine_rule_guided.py, rule_guided_bias.py, finalize_rule_guided_bias.py, rule_guided_verification.py, export_rule_guided_view.py, then rule_guided_report.py. The bias run may execute concurrently with refinement, but the finalizer must follow both. The historical reference has its own three reproducible scripts. Prior study kernels are unchanged. Only compact kernels, metrics, source and reports are retained; no dense training arrays are written.

| Condition | Selected start | Termination | Iterations |
|---|---|---|---:|
| Rule-guided initialization (lambda=0.75) | previous_fitted | Previous feasible fit retained | — |
| Rule-guided initialization (lambda=0.2) | previous_fitted | Previous feasible fit retained | — |
| Initial ch/sh preserved (lambda=0.75) | locked_frequency_start | STOP: TOTAL NO. of ITERATIONS REACHED LIMIT | 220 |
| Initial ch/sh preserved (lambda=0.2) | locked_frequency_start | STOP: TOTAL NO. of ITERATIONS REACHED LIMIT | 220 |
| Initial ch/sh preserved + family preference (0.03) | family_template | STOP: TOTAL NO. of ITERATIONS REACHED LIMIT | 220 |
| Initial ch/sh preserved + family preference (0.1) | family_template | STOP: TOTAL NO. of ITERATIONS REACHED LIMIT | 220 |
