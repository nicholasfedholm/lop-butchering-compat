"""Build the staged zip from src/ and verify every family present.
Usage: python -I build_verify.py <version>
Checks per family: JSON parse; patch file targets exist in the live LoP zip (read-only); /server|/client/behaviors arrays exist;
appended behaviors leave existing indices (ConfigLib pointers) untouched; every entity variant resolves (first match wins) to an
existing, non-skipped item variant with texture '1'; shapes, textures, reward items, blood item exist in Butchering 1.14.3;
lang key for every item; coverage rows non-empty. Then zip integrity + SHA256.
"""
import sys, os, json, glob, zipfile, hashlib, csv, fnmatch, itertools
sys.path.insert(0, os.path.dirname(__file__))
import lopresolve as L
import pyjson5
from gen_family import FAMILIES, MID, MODS, ROOT

BUT = os.path.join(ROOT, 'work', 'ex', 'butchering', 'assets', 'butchering')
VER = sys.argv[1] if len(sys.argv) > 1 else '0.1.0'
SRC = os.path.join(ROOT, 'src')
A = os.path.join(SRC, 'assets', MID)

def but_item_exists(code):
    dom, path = code.split(':')
    for f in glob.glob(os.path.join(BUT, 'itemtypes', '**', '*.json'), recursive=True):
        j = pyjson5.loads(open(f, encoding='utf-8-sig').read())
        c = j.get('code')
        if not c: continue
        if path == c or path.startswith(c + '-'):
            return True
    return False

fails = []
def check(cond, msg):
    if not cond: fails.append(msg)
    return cond

fams = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(A, 'patches', 'lop', '*.json')))
# modinfo + lang
modinfo = {"type": "content", "modid": MID, "name": "LoP Butchering Compat",
           "authors": ["Nick"], "description": "Butchering (1.14.x) carcass support for Legacy of the Phanerozoic families. Each family activates only if its LoP mod is installed. Yields come from each species' own LoP harvest drops.",
           "version": VER, "side": "Universal", "requiredOnClient": True, "requiredOnServer": True,
           "dependencies": {"game": "1.22.7", "butchering": "1.14.3"}}
json.dump(modinfo, open(os.path.join(SRC, 'modinfo.json'), 'w', encoding='utf-8'), indent=1)
lang = {}
for f in fams:
    lang.update(json.load(open(os.path.join(ROOT, 'work', 'lang', f + '.json'), encoding='utf-8')))
os.makedirs(os.path.join(A, 'lang'), exist_ok=True)
json.dump(lang, open(os.path.join(A, 'lang', 'en.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

butchering_shapes = {os.path.relpath(p, os.path.join(BUT, 'shapes')).replace('\\', '/')[:-5] for p in glob.glob(os.path.join(BUT, 'shapes', '**', '*.json'), recursive=True)}
butchering_tex = {os.path.relpath(p, os.path.join(BUT, 'textures')).replace('\\', '/')[:-4] for p in glob.glob(os.path.join(BUT, 'textures', '**', '*.png'), recursive=True)}
reward_ok = {}
summary = []
for fam in fams:
    nf0 = len(fails)
    it = pyjson5.loads(open(os.path.join(A, 'itemtypes', 'butchercreatures', fam + '.json'), encoding='utf-8').read())
    pt = pyjson5.loads(open(os.path.join(A, 'patches', 'lop', fam + '.json'), encoding='utf-8').read())
    zp = [z for z in glob.glob(os.path.join(MODS, FAMILIES[fam][0])) if '.bak' not in z][0]
    z = zipfile.ZipFile(zp)
    names = set(z.namelist())
    # item variants
    vg = it['variantgroups']
    allv = {f"{it['code']}-" + '-'.join(c) for c in itertools.product(*[g['states'] for g in vg])}
    valid = {v for v in allv if not any(fnmatch.fnmatchcase(v, s) for s in it.get('skipVariants', []))}
    check(all(any(g['code'] == 'texture' and '1' in g['states'] for g in [g]) for g in vg if g['code'] == 'texture'), f"{fam}: texture state 1 missing")
    for k, a in it['attributesByType'].items():
        for r in a['butcheringRewards'] + a['skinningRewards']:
            c = r['code']
            if c not in reward_ok: reward_ok[c] = but_item_exists(c)
            check(reward_ok[c], f"{fam}: reward item {c} not in Butchering")
        hs = a['hangingShape']['base'].split(':')[1]
        check(hs in butchering_shapes, f"{fam}: hanging shape {hs} missing")
        if 'bloodportion' not in reward_ok: reward_ok['bloodportion'] = but_item_exists(a['bloodType'])
        check(reward_ok['bloodportion'], f"{fam}: blood item missing")
    for k, s in it['shapeByType'].items():
        check(s['base'].split(':')[1] in butchering_shapes, f"{fam}: shape {s['base']} missing")
    for k, t in it['texturesByType'].items():
        for tt in t.values():
            d, p = tt['base'].split(':')
            check(d == 'game' or p in butchering_tex, f"{fam}: texture {tt['base']} missing")
    # patches
    ent_checked = 0; codes_ok = 0
    for p in pt:
        if p['path'] == '/enabled':
            check(p['file'] == f"{MID}:itemtypes/butchercreatures/{fam}.json" and it.get('enabled') is False, f"{fam}: enabled patch target wrong")
            continue
        dom, rel = p['file'].split(':', 1)
        zpath = f"assets/{dom}/{rel}"
        if not check(zpath in names, f"{fam}: patch target {zpath} not in {os.path.basename(zp)}"): continue
        ent = L.load_entity(zp, zpath)
        side = p['path'].split('/')[1]
        beh = ent.get(side, {}).get('behaviors')
        if not check(isinstance(beh, list) and p['path'] == f"/{side}/behaviors/-", f"{fam}: {zpath} {p['path']} not an append to an array"): continue
        before = json.dumps(beh)
        after = beh + [p['value']]
        check(json.dumps(after[:len(beh)]) == before, f"{fam}: index shift")
        ib = dict(p['value']['itemByType'])
        if os.environ.get('NEGTEST') == fam:  # corrupt in memory: drop first explicit key so it falls to '*'
            ib.pop([k for k in ib if k != '*'][-1])
        covmap = {r['entity']: r['item'] for r in csv.DictReader(open(os.path.join(ROOT, 'work', 'coverage', fam + '.csv'), encoding='utf-8'))}
        for code, _ in L.variants(ent):
            ent_checked += 1
            hit = next((v for k, v in ib.items() if L.wc_match(k, code)), None)
            if check(hit is not None, f"{fam}: {code} unmatched"):
                ic = hit.split(':', 1)[1]
                check(hit == covmap.get(code), f"{fam}: {code} resolves to {hit}, coverage says {covmap.get(code)}")
                if check(ic in valid, f"{fam}: {code} -> {ic} not a valid item variant"):
                    codes_ok += 1
                    stem = ic.rsplit('-', 2)[0]
                    check(f"item-{stem}-*" in lang, f"{fam}: lang key item-{stem}-* missing")
    cov = list(csv.DictReader(open(os.path.join(ROOT, 'work', 'coverage', fam + '.csv'), encoding='utf-8')))
    empty = [r for r in cov if not all(r.values())]
    check(not empty, f"{fam}: {len(empty)} empty coverage rows")
    summary.append(f"{fam}: entity-variant checks {codes_ok}/{ent_checked} ok, coverage rows {len(cov)} (empty {len(empty)}), items {len(valid)}, fails {len(fails) - nf0}")

# zip
os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
out = os.path.join(ROOT, 'out', f'{MID}_{VER}.zip')
if os.path.exists(out): os.remove(out)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for dp, _, fs in os.walk(SRC):
        for f in sorted(fs):
            full = os.path.join(dp, f)
            arc = os.path.relpath(full, SRC).replace('\\', '/')
            if f.endswith('.json'):
                json.loads(open(full, encoding='utf-8').read())  # strict parse
            zf.write(full, arc)
with zipfile.ZipFile(out) as zf:
    bad = zf.testzip(); nl = zf.namelist()
    for n in nl:
        if n.endswith('.json'): json.loads(zf.read(n).decode('utf-8'))
check(bad is None, f"zip testzip bad member {bad}")
sha = hashlib.sha256(open(out, 'rb').read()).hexdigest().upper()
print('\n'.join(summary))
print(f"zip {out} size={os.path.getsize(out)} files={len(nl)} sha256={sha} testzip={'OK' if bad is None else bad}")
for n in nl: print('  ', n)
print(f"FAILS: {len(fails)}")
for f in fails[:30]: print('  FAIL', f)
