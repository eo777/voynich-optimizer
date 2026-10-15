"""Verify the standalone publication without installing numerical packages."""
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def main():
    manifest = read('site-manifest.json')
    for name, meta in manifest['files'].items():
        p = ROOT / name
        assert p.is_file(), 'Missing file: ' + name
        raw = p.read_bytes()
        assert len(raw) == meta['bytes'], 'Changed size: ' + name
        assert hashlib.sha256(raw).hexdigest() == meta['sha256'], 'Changed hash: ' + name
    inventory = read('joint_word_explorer_manifest.json')
    corpus = read('data/chain_channels.json')
    assert inventory['words'] == corpus['words'], 'Word-index mismatch'
    assert len({m['id'] for m in inventory['models']}) == len(inventory['models'])
    assert inventory['default'] in {m['id'] for m in inventory['models']}
    assert len(inventory['models']) == manifest['models']
    max_error = 0.0
    stages_by_key = {s['key']: s for s in corpus['stages']}
    n = len(inventory['words'])
    for model in inventory['models']:
        d = read(model['file'])
        assert d['id'] == model['id']
        assert len(d['kernels']) == len(d['stages']) - 1
        assert math.isfinite(d['information_retained'])
        assert -1e-9 <= d['information_retained'] <= 1 + 1e-9
        mass = d['prior']
        assert len(mass) == n and abs(sum(mass) - 1) < 1e-8
        for t, stage in enumerate(d['stages']):
            source = stages_by_key[stage['key']]
            assert stage['tokens'] == source['N']
            assert stage['counts'] == [source['counts'].get(w, 0) for w in inventory['words']]
            assert len(stage['projected']) == n
            err = max(abs(a - b) for a, b in zip(mass, stage['projected']))
            max_error = max(max_error, err)
            assert err < 1e-8, 'Projected usage differs: ' + model['id']
            if t == len(d['kernels']):
                break
            totals = defaultdict(float)
            nxt = [0.0] * n
            for a, b, p in d['kernels'][t]:
                assert isinstance(a, int) and isinstance(b, int) and 0 <= a < n and 0 <= b < n
                assert math.isfinite(p) and 0 <= p <= 1 + 1e-9
                totals[a] += p
                nxt[b] += mass[a] * p
            assert max((abs(p - 1) for p in totals.values()), default=0) < 1e-8
            for i, p in enumerate(mass):
                if i not in totals:
                    nxt[i] += p
            assert abs(sum(nxt) - 1) < 1e-8
            mass = nxt
    print(json.dumps({'status': 'pass', 'files': len(manifest['files']),
                      'models': len(inventory['models']), 'words': len(inventory['words']),
                      'maximum_projection_error': max_error}))


if __name__ == '__main__':
    main()
