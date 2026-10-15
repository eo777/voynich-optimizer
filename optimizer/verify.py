"""Small numerical checks; replays saved kernels and never runs a model fit.

python -m optimizer.verify
Optional --original-study checks the port against original workspace sources;
normal standalone verification does not need those sources.
"""
from __future__ import annotations
import argparse
import importlib
import json
import sys
from pathlib import Path
import numpy as np
from .core import Chain
from .guidance import BiasedObjective, guided_seed, import_kernels
from .run import ROOT, configure, load_reference, provenance, read_json


def directional_error(value_grad, theta, weight, seed):
    rng = np.random.default_rng(seed)
    direction = rng.normal(size=len(theta))
    direction /= np.linalg.norm(direction)
    _, gradient = value_grad(theta, weight)
    epsilon = 1e-4
    finite = (value_grad(theta + epsilon * direction, weight)[0] -
              value_grad(theta - epsilon * direction, weight)[0]) / (2 * epsilon)
    return abs(float(finite - gradient @ direction))


def verify(data_path, reference_path, original_study=None):
    data, reference = read_json(data_path), load_reference(reference_path)
    chain = Chain(data, data['chain'].index(reference['start']))
    differences, row_errors, checked = [], [], 0
    for record in reference['records']:
        kernels = import_kernels(chain, record)
        actual = chain.metrics(kernels)
        differences.append(abs(actual['mean_frequency_mismatch'] - record['metrics']['mean_frequency_mismatch']))
        for a, expected in zip(actual['stages'], record['metrics']['stages']):
            for field in ('frequency_mismatch', 'information_bits', 'information_retained',
                          'common_information_retained', 'hapax_information_retained', 'attested_mass',
                          'exact_id_decoding', 'common_uncertainty_with_other_values_bits'):
                differences.append(abs(a[field] - expected[field]))
                checked += 1
        information = [s['information_retained'] for s in actual['stages']]
        assert all(b <= a + 1e-11 for a, b in zip(information, information[1:])), 'Source-blind propagation gained information'
        row_errors.extend(float(np.max(np.abs(np.asarray(k.sum(axis=1)).ravel() - 1))) for k in kernels)
    error = max(differences)
    assert error < 1e-10, error
    assert max(row_errors) < 1e-12, row_errors
    theta = chain.identity_theta(73)
    gradient_error = directional_error(chain.value_grad, theta, .2, 801)
    assert gradient_error < 1e-7, gradient_error
    locked_data, _ = configure(data, 'initial-lock')
    locked = Chain(locked_data, data['chain'].index('1b'))
    reference_record = next(r for r in reference['records'] if r['name'] == 'joint_0.75')
    objective = BiasedObjective(locked, reference_record, .1)
    bias_gradient_error = directional_error(objective.value_grad, locked.theta(objective.template), .75, 61)
    assert bias_gradient_error < 1e-7, bias_gradient_error
    result = {'passed': True, 'saved_records_replayed': len(reference['records']), 'stage_metric_checks': checked,
              'max_saved_metric_error': error, 'max_kernel_row_error': max(row_errors),
              'directional_gradient_error': gradient_error, 'family_bias_gradient_error': bias_gradient_error,
              'provenance': [provenance(data_path), provenance(reference_path)] +
                            [provenance(r['_model_path']) for r in reference['records'] if r.get('_model_path')],
              'full_fits_run': 0}
    if original_study:
        # Only a developer equivalence check; not a runtime dependency.
        sys.path.insert(0, str(Path(original_study).resolve()))
        original = importlib.import_module('joint_optimization')
        old_guide = importlib.import_module('rule_guided_optimization')
        old_bias = importlib.import_module('rule_guided_bias')
        old = original.Chain(original.D['chain'].index(reference['start']))
        old_f, old_g = old.value_grad(theta, .2)
        new_f, new_g = chain.value_grad(theta, .2)
        old_locked, _ = old_guide.make_chain(True)
        old_template, _ = old_guide.guided_seed(old_locked, reference_record, .5)
        new_template, _ = guided_seed(locked, reference_record, .5)
        template_error = max(float(np.max(np.abs(a.data - b.data))) for a, b in zip(old_template, new_template))
        old_obj = old_bias.BiasedObjective(old_locked, reference_record, .1)
        bias_theta = locked.theta(objective.template)
        of, og = old_obj.value_grad(bias_theta, .75)
        nf, ng = objective.value_grad(bias_theta, .75)
        result['original_equivalence'] = {'objective_error': abs(old_f - new_f),
            'gradient_max_error': float(np.max(np.abs(old_g - new_g))), 'guided_template_max_error': template_error,
            'bias_objective_error': abs(of - nf), 'bias_gradient_max_error': float(np.max(np.abs(og - ng)))}
        assert max(result['original_equivalence'].values()) < 1e-12, result
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', default=str(ROOT / 'data' / 'chain_channels.json'))
    p.add_argument('--reference', default=str(ROOT / 'data' / 'reference_1b.json'))
    p.add_argument('--original-study')
    p.add_argument('--output', help='Optional verification JSON; stdout always contains the result')
    args = p.parse_args()
    result = verify(args.data, args.reference, args.original_study)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
