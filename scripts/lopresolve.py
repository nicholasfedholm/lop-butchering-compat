"""Resolve LoP entity JSON per variant code (VS solveByType semantics: first matching key in order wins).
Library + CLI. Usage: python -I lopresolve.py <zip> <entity path in zip>  -> per-variant summary table.
"""
import sys, re, zipfile, json, itertools, fnmatch
import pyjson5

def load_entity(zpath, epath):
    with zipfile.ZipFile(zpath) as z:
        return pyjson5.loads(z.read(epath).decode('utf-8-sig'))

def wc_match(pattern, code):
    # VS WildcardUtil: '*' any, case-insensitive; '@' prefix = regex
    if pattern.startswith('@'):
        return re.fullmatch(pattern[1:], code, re.I) is not None
    return fnmatch.fnmatchcase(code.lower(), pattern.lower())

def solve(tok, code):
    if isinstance(tok, dict):
        out = {}
        for k, v in tok.items():
            if k.lower().endswith('bytype') and isinstance(v, dict):
                base = k[:-6]
                for pk, pv in v.items():
                    if wc_match(pk, code):
                        out[base] = solve(pv, code)
                        break
            else:
                if k not in out:
                    out[k] = solve(v, code)
        return out
    if isinstance(tok, list):
        return [solve(x, code) for x in tok]
    return tok

def variants(ent):
    groups = ent.get('variantgroups', [])
    states = [g['states'] for g in groups]
    codes = []
    for combo in itertools.product(*states):
        codes.append((ent['code'] + '-' + '-'.join(combo), dict(zip([g['code'] for g in groups], combo))))
    return codes

def harvest(resolved):
    for b in resolved.get('server', {}).get('behaviors', []):
        if b.get('code') == 'harvestable':
            return b
    return None

def tex_alternates(resolved):
    t = resolved.get('client', {}).get('texture')
    if isinstance(t, dict):
        return len(t.get('alternates', []) or [])
    return 0

if __name__ == '__main__':
    z, e = sys.argv[1], sys.argv[2]
    ent = load_entity(z, e)
    seen = set()
    for code, vg in variants(ent):
        r = solve(ent, code)
        h = harvest(r)
        drops = [] if not h else [f"{d.get('code')}:{(d.get('quantity') or {}).get('avg')}" for d in h.get('drops', [])]
        key = (vg.get('type'), vg.get('age'))
        if key in seen: continue
        seen.add(key)
        hb = r.get('hitboxSize') or {}
        print(f"{code}\thb={hb.get('x')}x{hb.get('y')}\tw={r.get('weight')}\talt={tex_alternates(r)}\t{' '.join(drops)}")
