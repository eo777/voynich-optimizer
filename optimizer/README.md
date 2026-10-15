# Standalone optimizer

This is the existing Echo7 fixed-prior information/frequency optimizer, extracted
without importing the Voynich research workspace. It is separate from the newer
preservation model. Frozen results in the website remain evidence from the original
study; a fresh run is saved separately and may find a different local solution.

Requires Python 3.9 or newer, NumPy and SciPy. From the exported repository root:

```sh
python -m pip install -r optimizer/requirements.txt
python -m optimizer.verify
python -m optimizer.run --mode named --start 1b --weight 0.75 --iterations 220 --seeds 2
python -m optimizer.run --mode ed2 --start 1b --weight 0.2 --iterations 120 --seeds 2
python -m optimizer.run --mode rule-initialized --weight 0.75 --seeds 2
python -m optimizer.run --mode initial-lock --weight 0.75 --seeds 2
python -m optimizer.run --mode family-bias --weight 0.75 --bias 0.1 --seeds 1
```

Use `--mode ed1` or `ed3` for the other generic supports, and `--bias 0.03` for
the weaker continuing family preference. `--start 1a` is supported for named and
generic modes. The rule-guidance schedule is restricted to its original `1b`
start; no new early-section schedule is invented by this extraction.

`--seeds` means the number of documented starting guesses, as in the study:
frequency and identity (random seed 31), plus an optional perturbed frequency
guess (seed 214) for named mode; 50% and 95% family guesses for guided modes;
one early-50%/later-95% template for continuing family bias. It is not an RNG seed.

## Inputs and outputs

- `data/chain_channels.json`: frozen ordered section counts, vocabulary, atomized
  spellings, rule labels and scheduled candidate edges.
- `data/joint_generic_candidates.json`: precomputed ED1/2/3 eligible edges. These
  use the original observed adjacent-section rates within a factor of two, and
  targets unclaimed by the original named-only allocation. The standalone tool
  does not regenerate that eligibility under a new fit.
- `data/reference_1a.json` and `data/reference_1b.json`: compact indexes with saved
  scalar metrics and references to the existing `joint_word_explorer/*.json`
  browser models. Kernels are loaded from those models without a duplicate raw
  research archive. The 1b index supplies starting guesses for guided modes.
  If it is missing, the frequency-only optimum supplies the initial nonfamily
  rows and the run records that fallback. `--reference PATH` accepts another
  compact index or a user-supplied full local named fit; its closest information
  weight is used only as an initializer while the requested objective is kept.
- Optional `--prior-candidates /path/to/local/locked-fits.json` accepts additional
  local locked fits for a family-bias run. These raw research files are not
  packaged. Without this custom input, the run does not claim to reproduce the
  original study's exact previous-candidate set.

Default outputs go to a new timestamped `runs/*.json`. `--output runs/example.json`
sets the path; `--detailed` adds per-word rates and endpoint compositions.
Existing output files require explicit `--overwrite`. Inputs, source and frozen
website results cannot be overwritten through the CLI. Nothing updates the website
or overwrites its frozen results automatically.

Each result contains all routing kernels, actual information and frequency
metrics, source hashes, the frequency-only LP certificate, convergence flags,
candidate scores and the selected initialization. Kernel triples use global word
indices from `data/chain_channels.json`. Words outside the active support persist
by identity. `records[2]` is the selected joint candidate; the first two records
are the frequency-only and exact identity controls.

## Method kept from the study

Each starting spelling is a unique synthetic identity with its observed token
prior. Every value arriving at the same spelling follows the same next-step
distribution. The objective is mean total-variation frequency mismatch across
all later sections plus `weight` times final fractional identity-information loss.
The starting prior never changes to make section frequencies fit.

Named mode uses the frozen named candidate support, including tentative rules.
Generic modes extend that support with the frozen edit-distance candidates.
The initial-class lock forbids all crossing between initial `ch`, initial `sh`
and other spellings, including deletion/attachment routes. The continuing family
preference adds the original mass-weighted routing KL penalty, normalized by
transition count and fixed starting family mass. Its 50%/95% templates and
0.03/0.1 weights are assumptions, not recovered historical rates.

Exact feasible seeds remain candidates under the actual unsmoothed objective,
including the frequency-only solution. This retains the study's correction for
searches that worsen an exact seed. The search itself uses the original smoothed
TV objective, analytic gradient, bounded L-BFGS-B settings and source-blind
kernels. The family-bias result reports both the base and penalized objectives.
No averaging of separately fitted codebooks is performed.

Frequency-only optimization has a global mean-TV lower-bound certificate for its
support. Joint optimization is nonconvex and iteration-limited: a successful
solver return is not proof of a global information optimum. Information here is
starting-spelling identity, not semantics. Fixed-frequency mismatch also includes
ordinary changes in usage; historical abbreviation comparisons must distinguish
that from collisions in the written representation.

## Verification and resource use

`python -m optimizer.verify` replays every saved named fit, compares the original
stage metrics, checks stochastic kernels and nonincreasing information, and checks
analytic directional gradients for both the base and family-bias objectives.
It performs no fit. `verification.json` records the extraction-time check against
the original sources. Its optional `--original-study PATH` developer check is not
a standalone runtime dependency.

New fits can take minutes or longer, especially ED3. The CLI prints the estimated
joint-array RAM before optimization; optimizer temporaries add to that amount.
No dense model/checkpoint arrays are written. Typical compact run files contain
sparse kernels and small metric tables; use `--detailed` only when needed. Solver
versions and stopping limits can change the selected local candidate.
