"""Run the frozen Echo7 optimizer outside the research workspace.

From the exported repository: python -m optimizer.run --help
The local source package is apps.echo_optimizer.engine.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.optimize import minimize
from .core import Chain
from .guidance import (BiasedObjective, actual_objective, focus, guided_seed,
                       import_kernels, initial_class)

ROOT = Path(__file__).resolve().parents[1]
MODES = ('named', 'ed1', 'ed2', 'ed3', 'rule-initialized', 'initial-lock', 'family-bias')
GUIDED = ('rule-initialized', 'initial-lock', 'family-bias')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def load_reference(path, root=None):
    """Load compact published references, or full local study records.

    Compact records name an existing browser model instead of duplicating its
    kernels. Model paths are relative to the standalone repository root and
    must resolve inside it. Original records with inline kernels still work.
    """
    doc = read_json(path)
    root = Path(root or ROOT).resolve()
    for record in doc['records']:
        if 'kernels' in record:
            continue
        relative = Path(record['model_file'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError(f'Model file must be a relative path inside the repository: {relative}')
        model_path = (root / relative).resolve()
        if root not in model_path.parents or model_path.suffix.lower() != '.json':
            raise ValueError(f'Model file must resolve to JSON inside the repository: {relative}')
        payload = read_json(model_path)
        if payload.get('start', doc['start']) != doc['start']:
            raise ValueError(f'Model start disagrees with reference: {relative}')
        if not isinstance(payload.get('kernels'), list) or not payload['kernels']:
            raise ValueError(f'Model contains no routing kernels: {relative}')
        record['kernels'] = payload['kernels']
        record['_model_path'] = str(model_path)
    return doc


def provenance(path):
    path = Path(path)
    return {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def guard_output(path, input_paths=(), overwrite=False, root=None):
    """Protect source, frozen runtime data and every manifest-owned site file."""
    root = Path(root or ROOT).resolve()
    destination = Path(path).resolve()
    for frozen in ('data', 'research', 'site', 'joint_word_explorer', 'optimizer', 'engine'):
        protected = (root / frozen).resolve()
        if destination == protected or protected in destination.parents:
            raise ValueError(f'Output must not replace frozen inputs or source under {protected}')
    manifest_path = root / 'site-manifest.json'
    managed = {manifest_path.resolve()}
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        for name in manifest['files']:
            managed.add((root / name).resolve())
    if destination in managed:
        raise ValueError(f'Output must not replace a published manifest-owned file: {destination}')
    if any(destination == Path(p).resolve() for p in input_paths if p):
        raise ValueError('Output must not overwrite an input file')
    if destination.exists() and not overwrite:
        raise ValueError('Output already exists; choose another filename or explicitly pass --overwrite')
    return destination


def configure(data, mode, candidates=None):
    """Copy the frozen data before adding generic edges or applying the lock."""
    if mode not in MODES:
        raise ValueError(f'Unknown mode: {mode}')
    result = copy.deepcopy(data)
    edges = result['menus']['scheduled_v22']['step_edges']
    additions, removed = {}, {}
    if mode.startswith('ed'):
        if candidates is None:
            raise ValueError('Generic modes need the frozen generic candidate input')
        distance = int(mode[-1])
        for key, values in candidates.items():
            extra = [(a, b, 1., [], 1) for a, b, d in values if d <= distance]
            edges[key].extend(extra)
            additions[key] = len(extra)
    if mode in ('initial-lock', 'family-bias'):
        words = result['words']
        for key, values in edges.items():
            keep = [e for e in values if initial_class(words[e[0]]) == initial_class(words[e[1]])]
            removed[key] = len(values) - len(keep)
            edges[key] = keep
    return result, {'generic_candidate_counts': additions, 'removed_edge_counts': removed}


def select_reference(path, weight, start):
    """A saved fit is a starting guess, never silently a changed dataset."""
    doc = load_reference(path)
    if doc['start'] != start:
        raise ValueError(f'Reference starts at {doc["start"]}, requested {start}')
    candidates = [r for r in doc['records'] if r.get('weight') is not None and 'kernels' in r]
    if not candidates:
        raise ValueError('Reference has no fitted kernel record')
    # An exact weight is used when available. Otherwise the closest saved
    # weight is just a feasible initializer; the requested objective is kept.
    return min(candidates, key=lambda r: abs(float(r['weight']) - weight))


def identity_kernels(chain):
    return [sparse.csr_matrix((np.where(a == b, 1., 0.), b, ptr), shape=(chain.n, chain.n))
            for a, b, ptr in chain.edges]


def search(chain, initial, weight, iterations, label, objective=None, generic=False):
    """The original bounded L-BFGS-B search; preserve the exact seed as a candidate."""
    value_grad = chain.value_grad if objective is None else objective.value_grad
    actual = (lambda ks: actual_objective(chain, ks, weight)) if objective is None else (lambda ks: objective.actual(ks, weight))
    tick, counter = [time.monotonic()], [0]
    def callback(_):
        counter[0] += 1
        if time.monotonic() - tick[0] > 30:
            print(f'{label}: iteration {counter[0]}', flush=True)
            tick[0] = time.monotonic()
    initial_score = actual(initial)
    fit = minimize(value_grad, chain.theta(initial), args=(weight,), jac=True, method='L-BFGS-B',
                   bounds=[(-25, 25)] * chain.size, callback=callback,
                   options={'maxiter': iterations, 'ftol': 1e-11, 'gtol': 1e-7,
                            'maxcor': 8 if generic else 12, 'maxls': 25 if generic else 30})
    fitted = chain.kernels(fit.x)
    fitted_score = actual(fitted)
    use_seed = initial_score < fitted_score
    selected = initial if use_seed else fitted
    meta = {'name': label, 'selected': 'exact_initial_seed' if use_seed else 'optimized',
            'initial_objective': initial_score, 'searched_objective': fitted_score,
            'objective': min(initial_score, fitted_score), 'iterations': int(fit.nit),
            'success': bool(fit.success), 'message': str(fit.message),
            'final_smoothed_objective': float(fit.fun), 'global_optimum_claimed': False}
    print(f'{label}: objective {meta["objective"]:.8f}; {meta["selected"]}; {fit.nit} iterations', flush=True)
    return selected, meta


DEFINITIONS = {
    'objective': 'Mean total-variation mismatch over all later sections + weight times final fractional loss of distinct starting-spelling information.',
    'prior': 'Each starting spelling is a distinct synthetic value with count / full starting-section token total. Fixed during propagation.',
    'kernel': 'Each current spelling has one routing distribution shared by every source value. A merge cannot be reversed by secretly using ancestry.',
    'support': 'Identity plus frozen scheduled named candidate edges with observed destinations, including tentative rules. Identity may persist unattested and then contributes frequency mismatch.',
    'generic': 'Named support plus frozen atomic ED<=k candidates, observed adjacent-section rates within factor two, destination unclaimed in the original saved named allocation. Eligibility is not recomputed from fitted rates.',
    'lock': 'Initial ch, initial sh, and other are separate partitions. Cross-partition routes, including bench deletion/attachment, are forbidden.',
    'guidance': 'Only existing forward S1/C1.1 early and B1/C1 later routes are favored. Rule-initialized/initial-lock try 50% and 95% guesses; family-bias keeps a KL preference active: 50% early, 95% later, otherwise identity on eligible liquid/edy rows.',
    'common': 'At least ten starting-section occurrences. Common information conditions on that cohort; uncertainty against other values is separately reported.',
    'limits': 'Conditional synthetic identity simulation, not meanings or historical ancestry. Frequency-only LP certifies minimum mean-TV on this support. Information-aware optimization is local and nonconvex; no global optimum is claimed.',
    'selection': 'Actual unsmoothed objective selects among exact feasible seeds, searched solutions and explicitly supplied prior candidates. No averaging of codebooks.',
}


def run(args):
    started = time.monotonic()
    data_path = Path(args.data)
    original = read_json(data_path)
    candidate_path = Path(args.candidates)
    generic = args.mode.startswith('ed')
    data, counts = configure(original, args.mode, read_json(candidate_path) if generic else None)
    c = Chain(data, data['chain'].index(args.start))
    print(f'{args.mode}, {args.start}: {c.n} active spellings, {len(c.prior)} active values, {c.size} parameters', flush=True)
    # Most cost is dense source-by-spelling joints in RAM; no arrays are saved.
    print('Estimated joint-array RAM: %.0f MiB before optimizer temporaries' %
          ((c.T + 1) * len(c.prior) * c.n * 8 / 2**20), flush=True)
    lp, certificate = c.frequency_optimum()
    lp_metrics = c.metrics(lp, detailed=args.detailed)
    if abs(lp_metrics['mean_frequency_mismatch'] - certificate['mean_tv_lower_bound']) > 1e-7:
        raise AssertionError('LP replay disagrees with its mean-TV certificate')
    ident = identity_kernels(c)
    records = [{'name': 'frequency_only', 'weight': 0., 'metrics': lp_metrics,
                'kernels': c.export_kernels(lp), 'solver': certificate},
               {'name': 'identity_control', 'weight': None, 'metrics': c.metrics(ident, detailed=args.detailed),
                'kernels': c.export_kernels(ident)}]
    files = [data_path, Path(__file__), Path(__file__).with_name('core.py'), Path(__file__).with_name('guidance.py')]
    if generic:
        files.append(candidate_path)
    reference = {'name': 'frequency_only', 'weight': 0., 'kernels': c.export_kernels(lp)}
    reference_note = 'Frequency optimum; no saved fitted reference used.'
    reference_path = Path(args.reference) if args.reference else ROOT / 'data' / f'reference_{args.start}.json'
    if args.mode in GUIDED and reference_path.exists():
        reference = select_reference(reference_path, args.weight, args.start)
        reference_note = f'{reference_path.name}: {reference["name"]}; initializer only'
        files.append(reference_path)
        if reference.get('_model_path'):
            files.append(Path(reference['_model_path']))
    elif args.reference:
        raise FileNotFoundError(reference_path)
    objective = BiasedObjective(c, reference, args.bias) if args.mode == 'family-bias' else None
    score = (lambda ks: actual_objective(c, ks, args.weight)) if objective is None else (lambda ks: objective.actual(ks, args.weight))
    eligible = []
    def keep(ks, label):
        eligible.append((score(ks), ks, {'name': label, 'selected': 'existing_feasible_candidate'}))
    # Keep exact feasible solutions eligible, including ED3's frequency seed.
    keep(lp, 'exact_frequency_seed')
    keep(ident, 'exact_identity_control')
    if args.mode in GUIDED:
        keep(import_kernels(c, reference), 'projected_reference' if args.mode != 'rule-initialized' else 'reference')
    if args.mode == 'family-bias':
        starts = [('family_template', objective.template)]
        if args.prior_candidates:
            prior_path = Path(args.prior_candidates)
            previous = read_json(prior_path)
            if previous['start'] != args.start:
                raise ValueError('Prior candidate start differs from requested start')
            for record in previous['records']:
                if record.get('locked') and record.get('weight') == args.weight:
                    keep(import_kernels(c, record), 'previous_locked_fit')
            files.append(prior_path)
    elif args.mode in GUIDED:
        starts = [(f'rule_seed_{share:g}', guided_seed(c, reference, share)[0]) for share in (.5, .95)]
    else:
        starts = [('frequency_warm_start', lp), ('identity_start', c.kernels(c.identity_theta(31)))]
        if args.seeds == 3:
            theta = c.theta(lp) + np.random.default_rng(214).normal(0, 1., c.size)
            starts.append(('perturbed_frequency_start', c.kernels(theta)))
    attempts = []
    for name, initial in starts[:args.seeds]:
        fitted, meta = search(c, initial, args.weight, args.iterations, name, objective, generic)
        eligible.append((score(fitted), fitted, meta))
        attempts.append(meta)
    eligible.sort(key=lambda item: item[0])
    selected_score, ks, selected = eligible[0]
    record = {'name': 'joint_selected', 'weight': args.weight, 'locked': args.mode in ('initial-lock', 'family-bias'),
              'objective': actual_objective(c, ks, args.weight), 'metrics': c.metrics(ks, detailed=args.detailed),
              'kernels': c.export_kernels(ks), 'optimization': {**selected, 'starts': attempts,
                  'candidate_objectives': [{'name': m['name'], 'objective': v} for v, _, m in eligible],
                  'global_optimum_claimed': False}}
    if args.mode in GUIDED:
        record['focus'] = focus(c, ks)
    if objective is not None:
        record.update(bias_strength=args.bias, penalized_objective=selected_score,
                      family_penalty=objective.penalty(ks), penalty_initial_family_mass=objective.starting_family_mass)
    records.append(record)
    result = {'schema': 'echo7.portable_joint_optimizer.v1', 'start': args.start,
              'chain': [s['key'] for s in c.stages], 'source_entropy_bits': c.h,
              'configuration': {'mode': args.mode, 'weight': args.weight, 'bias': args.bias if objective else None,
                                'iterations': args.iterations, 'seeds': args.seeds, 'reference': reference_note},
              **counts, 'active_words': c.n, 'active_initial_values': len(c.prior),
              'total_initial_values': len(c.all_prior), 'frequency_certificate': certificate,
              'records': records, 'definitions': DEFINITIONS, 'provenance': [provenance(p) for p in files],
              'seconds': time.monotonic() - started}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation keeps a typo from replacing another completed run.
    with output.open('w' if args.overwrite else 'x', encoding='utf-8') as handle:
        json.dump(result, handle, separators=(',', ':'), allow_nan=False)
    print(f'Saved {output} ({output.stat().st_size / 2**20:.2f} MiB)', flush=True)
    print('Selected: mean mismatch %.4f, final identity information %.4f' %
          (record['metrics']['mean_frequency_mismatch'], record['metrics']['stages'][-1]['information_retained']), flush=True)
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=MODES, default='named')
    p.add_argument('--start', choices=('1a', '1b'), default='1b')
    p.add_argument('--weight', type=float, default=None, help='Information-loss weight; default .2 for generic modes, .75 otherwise')
    p.add_argument('--bias', type=float, choices=(.03, .1), default=.1, help='Continuing family preference strength')
    p.add_argument('--iterations', type=int, default=220)
    p.add_argument('--seeds', type=int, default=None, help='Number of documented starting guesses, not an RNG seed')
    p.add_argument('--data', default=str(ROOT / 'data' / 'chain_channels.json'))
    p.add_argument('--candidates', default=str(ROOT / 'data' / 'joint_generic_candidates.json'))
    p.add_argument('--reference', help='Optional compact reference index or local saved named fit for guided modes')
    p.add_argument('--prior-candidates', help='Optional user-supplied local locked fits for family-bias candidates; not packaged')
    p.add_argument('--output', help='New run JSON; default runs/<mode>_<start>_<UTC timestamp>.json')
    p.add_argument('--detailed', action='store_true', help='Also write per-word marginal tables and final endpoint compositions')
    p.add_argument('--overwrite', action='store_true', help='Replace an existing run output; frozen inputs and site remain protected')
    return p


def main():
    p = parser()
    args = p.parse_args()
    if args.weight is None:
        args.weight = .2 if args.mode.startswith('ed') else .75
    if not math.isfinite(args.weight) or args.weight < 0:
        p.error('--weight must be finite and nonnegative')
    if args.iterations < 1:
        p.error('--iterations must be positive')
    if args.mode in GUIDED and args.start != '1b':
        p.error('The frozen rule-guidance schedule was evaluated from 1b; use named/ed1/ed2/ed3 for a 1a start')
    max_seeds = 1 if args.mode == 'family-bias' else (2 if args.mode in GUIDED or args.mode.startswith('ed') else 3)
    args.seeds = min(2, max_seeds) if args.seeds is None else args.seeds
    if not 1 <= args.seeds <= max_seeds:
        p.error(f'--seeds must be between 1 and {max_seeds} for {args.mode}')
    if args.reference and args.mode not in GUIDED:
        p.error('--reference is only used by guided modes')
    if args.prior_candidates and args.mode != 'family-bias':
        p.error('--prior-candidates is only used by family-bias')
    if not args.output:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        args.output = str(ROOT / 'runs' / f'{args.mode}_{args.start}_{stamp}.json')
    input_paths = [args.data, args.candidates, args.reference, args.prior_candidates]
    try:
        guard_output(args.output, input_paths, args.overwrite)
    except ValueError as error:
        p.error(str(error))
    run(args)


if __name__ == '__main__':
    main()
