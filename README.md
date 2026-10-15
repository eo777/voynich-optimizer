# Voynich optimizer

Can proposed Voynich spelling transformations preserve information while matching word usage across manuscript sections?

This standalone app explores the simple Echo optimizer: a whole-chain search balancing frequency mismatch against loss of distinct starting-word identities. It includes 24 saved models, a word-by-word explorer, rule-guided variants, and Latin abbreviation and Vulgate frequency references. The Python optimizer and its frozen inputs are included; the original research workspace is not required.

## Open the app

Open the [live app](https://eo777.github.io/voynich-optimizer/). GitHub Pages publishes the `main` branch and repository root.

To run locally, serve this directory:

```sh
python -m http.server 8782 --bind 127.0.0.1
```

Open [localhost:8782](http://127.0.0.1:8782/). Use a web server rather than opening the HTML directly: the explorer loads its data with `fetch`. No backend, accounts, build step or JavaScript dependencies are required to view saved results.

For a concrete path, open [chol under the stronger family preference](https://eo777.github.io/voynich-optimizer/?word=chol&condition=guided-1b-family_bias_0.1#word-explorer). The selector covers 6,903 spellings. All sections are visible together, with observed counts, projected usage, incoming values and the selected source value's destinations.

## What is measured

Each spelling in the starting section has a unique synthetic identity and probability equal to its observed token share. All values currently sharing one spelling follow the same transition probabilities. A rename can preserve an identity; a merge can destroy the distinction between identities.

The base objective is:

`mean section frequency mismatch + information weight × final fractional identity-information loss`

Frequency mismatch is total variation between projected and observed spelling frequencies. Identity information is mutual information divided by starting entropy. Common-word scores condition on words occurring at least ten times in the starting section. These are different quantities with different denominators.

Named-rule, generic one-/two-/three-edit, initial-class-preserving and family-biased conditions make different assumptions. Family preference changes the objective; it is not an independent discovery of that path. The permitted graph includes tentative correspondences. Starting usage is fixed during propagation, and a spelling may retain identity while absent from a later section, incurring frequency mismatch.

These are conditional feasibility experiments, not decipherments or recovered historical lineages. Information-aware searches are local and do not prove a global optimum. Unchanged meanings can have changing usage; historical abbreviation collision loss and forward frequency mismatch must be assessed separately.

- [Joint optimizer methods and results](JOINT_OPTIMIZATION_RESULTS.md)
- [Rule-guided methods and historical comparisons](RULE_GUIDED_RESULTS.md)
- [Latin reference study](historical_reference.html)
- [Python optimizer instructions](optimizer/README.md)

The two research reports preserve the study's original results and reproduction history. Use the standalone Python instructions for paths and commands in this repository.

## Run a new optimization

Python 3.9 or newer, NumPy and SciPy are needed for fitting. Viewing the app does not require them.

```sh
python -m pip install -r optimizer/requirements.txt
python -m optimizer.run --help
python -m optimizer.verify
```

New runs are written separately from the frozen published models; see the optimizer instructions for examples and resource estimates. The browser displays the verified saved fits until an explicitly refreshed dataset is published.

## Verify the package

```sh
python check.py
python -m optimizer.verify
```

The first command uses only the Python standard library. It checks the publication hashes, all model files, transition rows and corpus alignment. The second checks the numerical optimizer against compact reference metrics. `optimizer/verification.json` records the extraction-time comparison with the original calculations.

## Contents

| Path | Contents |
|---|---|
| `index.html`, `*.js`, `*.mjs` | Static results and word explorer |
| `joint_word_explorer/` | 24 saved stochastic models, loaded on demand |
| `data/` | Frozen section counts, atomic glyph units, scheduled rule graph, generic candidates and compact reference metrics |
| `optimizer/` | Portable Python implementation and numerical checks |
| `historical_reference*` | Latin abbreviation and Vulgate comparison metrics, provenance and explanation |
| `site-manifest.json` | File hashes and original source-artifact hashes |

## Data and related work

Voynich counts and candidate rules are the frozen Echo study snapshot of 14–15 October 2026. Text derives from the Zandbergen–Landini transliteration; the proposed Golf 2.1 section order is a study assumption. `data/chain_channels.json` retains units, section counts, rule labels, scopes, definitions and source hashes. This snapshot does not automatically adopt later rule-catalogue changes.

The Latin reference page links the ORIFLAMMS manuscript datasets, the Saint-Victor release and the Clementine Vulgate source, with revisions and analysis choices in the metric files. The package includes derived measurements, not the upstream image collections. Reported abbreviation figures are finite-sample spelling-identity measurements, not universal semantic-loss estimates.

Related apps: [Echo rule analyzer](https://eo777.github.io/voynich-rules/) and [Voynich clusters](https://eo777.github.io/voynich-clusters/).

This is the simple joint optimizer, separate from the newer Echo preservation-model workstream. The package is exported from a research workspace, but is runnable on its own. Only app assets, executable source and their required inputs are included. The Python tool reuses the browser's saved kernels; duplicate research archives, optimizer output directories, unrelated studies and temporary model arrays are excluded.
