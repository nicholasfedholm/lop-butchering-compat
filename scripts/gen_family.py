"""Generate lopbutcheringcompat assets for one LoP family (native carcass design, AUDIT.md sections 5-6).
Usage: python -I gen_family.py <family_key>   (keys in FAMILIES)
Writes src/assets/lopbutcheringcompat/{itemtypes,patches}/<domain>.json, src/lang fragments, work/coverage/<domain>.csv
"""
import sys, os, json, zipfile, glob, csv, re
sys.path.insert(0, os.path.dirname(__file__))
import lopresolve as L
import pyjson5

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODS = os.environ.get('VS_MODS') or os.path.join(os.environ.get('APPDATA', ''), 'VintagestoryData', 'Mods')
MID = 'lopbutcheringcompat'
SKIP = ('egg', 'nest', 'lure', 'hitch')

# family key -> (zip glob, diet)
FAMILIES = {
    'abelisauridae': ('LoP-Abeli-*.zip', 'carn'),
    'tyrannosauridae': ('LoP-Tyranno-*.zip', 'carn'),
    'ceratopsidae': ('lop-ceratops-*.zip', 'herb'),
    'hadrosauroidea': ('LoP-Hadro-*.zip', 'herb'),
    'carcharodontosauridae': ('LoP-Carchar-*.zip', 'carn'),
    'spinosauridae': ('LoP-Spino-*.zip', 'carn'),
    'dromaeosauridae': ('LoP-Dromaeo-*.zip', 'carn'),
    'ankylosauria': ('LoP-Ankylo-*.zip', 'herb'),
    'stegosauria': ('LoP-Stego-*.zip', 'herb'),
    'therizinosauridae': ('LoP-Theriz-*.zip', 'herb'),
    'pachycephalosauria': ('LoP-Pachy-*.zip', 'herb'),
    'ornithomimosauria': ('LoP-Ornitho-*.zip', 'herb'),
    'macronaria': ('LoP-Macrons-*.zip', 'herb'),
    'mosasauridae': ('LoP-Mosa-*.zip', 'carn'),
    'allosauridae': ('LoP-Allosauridae-*.zip', 'carn'),
    'compsognathidae': ('LoP-Compsognathidae-*.zip', 'carn'),
    'diplodocoidea': ('LoP-Diplodocoidea-*.zip', 'herb'),
    'herrerasauridae': ('LoP-Herrerasauridae-*.zip', 'carn'),
    'ichthyosauria': ('LoP-Ichthyosauria-*.zip', 'carn'),
    'iguanodontia': ('LoP-Iguanodontia-*.zip', 'herb'),
    'oviraptorosauria': ('LoP-Oviraptorosauria-*.zip', 'herb'),
    'plateosauridae': ('LoP-Plateosauridae-*.zip', 'herb'),
    'plesiosauria': ('LoP-Plesiosauria-*.zip', 'carn'),
    'pterosauria': ('LoP-Pterosauria-*.zip', 'carn'),
}

# anchors: Butchering 1.14.3 itemtypes/butchercreatures/<file> (see AUDIT.md section 6)
def R(code, avg, var):
    return {"type": "item", "code": "butchering:" + code, "quantity": {"avg": avg, "var": var}}
ANCH = {
    ('small', 'carn'): dict(mass=0.01, blood=50, wl='small', shape='genericsmall/small', src='fox.json', br=[R('sinew-wet', 1.6, 0.4), R('offal-bloody', 1.6, 0.4)]),
    ('small', 'herb'): dict(mass=0.01, blood=50, wl='small', shape='genericsmall/small', src='hare.json', br=[R('offal-bloody', 1.6, 0.4)]),
    ('medium', 'carn'): dict(mass=0.03, blood=100, wl='medium', shape='genericmedium/medium', src='wolf.json', br=[R('sinew-wet', 3, 1), R('offal-bloody', 1.6, 0.4)]),
    ('medium', 'herb'): dict(mass=0.03, blood=100, wl='medium', shape='genericmedium/medium', src='pig.json', br=[R('primemeat-raw', 3, 1), R('offal-bloody', 4, 1)]),
    ('large', 'carn'): dict(mass=0.1, blood=400, wl='large', shape='genericlarge/large', src='bear.json (brown)', br=[R('sinew-wet', 3, 1), R('offal-bloody', 4, 1)]),
    ('large', 'herb'): dict(mass=0.06, blood=400, wl='large', shape='genericlarge/large', src='moose.json', br=[R('primemeat-raw', 2, 1), R('offal-bloody', 3, 1)]),
    ('giant', '*'): dict(mass=0.16, blood=400, wl='large', shape='generichuge/huge', src='elephantidae/elephantidae.json (male)', br=[R('primemeat-raw', 6, 2), R('offal-bloody', 3, 0.5)]),
    ('colossal', '*'): dict(mass=0.4, blood=400, wl='large', shape='generichuge/huge', src='elephantidae/elephantidae.json (male); mass 0.4 = slowdown clamp', br=[R('primemeat-raw', 6, 2), R('offal-bloody', 3, 0.5)]),
}
ORDER = ['small', 'medium', 'large', 'giant', 'colossal']

def anchor(cls, diet):
    return ANCH.get((cls, diet)) or ANCH[(cls, '*')]

def cls_meat(m):
    return 'small' if m < 8 else 'medium' if m < 30 else 'large' if m < 120 else 'giant' if m <= 250 else 'colossal'

def cls_hb(y):
    if not y: return 'small'
    return 'small' if y < 0.8 else 'medium' if y < 1.6 else 'large' if y < 4.5 else 'giant' if y < 8 else 'colossal'

MEATY = ('meat', 'poultry', 'fish', 'bushmeat', 'redmeat')

def main(fam):
    zg, diet = FAMILIES[fam]
    zp = [z for z in glob.glob(os.path.join(MODS, zg)) if '.bak' not in z]
    assert len(zp) == 1, zp
    zp = zp[0]
    z = zipfile.ZipFile(zp)
    mi = pyjson5.loads(z.read('modinfo.json').decode('utf-8-sig'))
    modid = mi.get('modid') or mi.get('modID') or mi.get('modId')
    lang = {}
    ln = [n for n in z.namelist() if n.endswith('lang/en.json')]
    if ln:
        lang = pyjson5.loads(z.read(ln[0]).decode('utf-8-sig'))
    ents = [n for n in z.namelist() if '/entities/' in n and n.endswith('.json') and not any(s in os.path.basename(n) for s in SKIP)]
    rows = []      # coverage rows
    groups = {}    # (species, age) -> dict
    patches = []
    for e in sorted(ents):
        ent = L.load_entity(zp, e)
        domain = e.split('/')[1]
        file_ref = f"{domain}:{e.split('/', 2)[2]}"
        item_by = {}
        for code, vg in L.variants(ent):
            r = L.solve(ent, code)
            h = L.harvest(r)
            if not h:
                rows.append(dict(entity=code, file=file_ref, item='', cls='', yield_source='NO HARVESTABLE', anchor=''))
                continue
            age = vg.get('age', 'adult')
            sp = vg.get('type') or '-'.join(v for k, v in vg.items() if k not in ('age', 'gender', 'sex')) or ent['code']
            meat = sum((d.get('quantity') or {}).get('avg') or 0 for d in h.get('drops', []) if any(m in str(d.get('code')) for m in MEATY))
            hb = (r.get('hitBoxSize') or {}).get('y')
            cls = max(cls_meat(meat), cls_hb(hb), key=ORDER.index)
            key = (sp, age)
            g = groups.setdefault(key, dict(cls=cls, codes=[], drops=set()))
            if ORDER.index(cls) > ORDER.index(g['cls']): g['cls'] = cls
            g['codes'].append(code)
            g['drops'].update(f"{d.get('code')}" for d in h.get('drops', []))
            item = f"{MID}:dead{fam}-{sp}-{age}-1-dead"
            item_by[code] = item
            rows.append(dict(entity=code, file=file_ref, item=item, cls=None, yield_source='LoP harvestable drops: ' + ' '.join(f"{d.get('code')}:{(d.get('quantity') or {}).get('avg')}" for d in h.get('drops', [])), anchor=None, key=key))
        if not item_by:
            continue
        # fallback for any code not listed: first-match-wins, '*' last
        fb_key = max(groups, key=lambda k: ORDER.index(groups[k]['cls']))
        item_by['*'] = f"{MID}:dead{fam}-{fb_key[0]}-{fb_key[1]}-1-dead"
        for side in ('server', 'client'):
            patches.append({"op": "add", "path": f"/{side}/behaviors/-", "value": {"code": "butcherable", "itemByType": item_by},
                            "file": file_ref, "dependsOn": [{"modid": modid}]})
    for r_ in rows:
        if 'key' in r_:
            g = groups[r_.pop('key')]
            r_['cls'] = g['cls']; r_['anchor'] = anchor(g['cls'], diet)['src']
    species = sorted({k[0] for k in groups}); ages = sorted({k[1] for k in groups})
    # itemtype
    attrs, shapes = {}, {}
    for (sp, age), g in sorted(groups.items()):
        a = anchor(g['cls'], diet)
        k = f"dead{fam}-{sp}-{age}-1-*"
        skin = []
        attrs[k] = {"size": 0.5, "mass": a['mass'], "bloodType": "butchering:bloodportion", "bloodAmount": a['blood'],
                    "butcheringWorkLoad": a['wl'], "handbookByType": {"*-rotten": {"exclude": False}, "*": {"exclude": True}},
                    "hangingShape": {"base": f"butchering:creatures/modded/{a['shape']}-hanging"},
                    "excludeRewards": [], "butcheringRewards": a['br'], "skinningRewards": skin}
        shapes[k] = {"base": f"butchering:creatures/modded/{a['shape']}-dead"}
    # combos not produced by the entity (e.g. species only has adult) are disabled via skipVariants
    allc = {(s, a_) for s in species for a_ in ages}
    skipv = [f"dead{fam}-{s}-{a_}-*" for (s, a_) in sorted(allc - set(groups))]
    tex = {}
    for st, t in (('dead', ('animalredmeatbloody', None)), ('skinned', ('animalredmeatbloody',) * 2), ('bledout', ('animalredmeatbledout',) * 2)):
        tex[f"*-{st}"] = {"meat": {"base": f"butchering:item/butchercreatures/{t[0]}"}} if st == 'dead' else {
            "fur": {"base": f"butchering:item/butchercreatures/{t[0]}"}, "meat": {"base": f"butchering:item/butchercreatures/{t[1]}"}}
    tex["*-rotten"] = {"fur": {"base": "game:block/creature/rot/rot"}, "meat": {"base": "game:block/creature/rot/rot"}}
    itype = {
        "enabled": False, "code": f"dead{fam}", "class": "butcherable",
        "variantgroups": [{"code": "species", "states": species}, {"code": "age", "states": ages},
                          {"code": "texture", "states": ["1"]}, {"code": "state", "states": ["dead", "skinned", "bledout", "rotten"]}],
        "skipVariants": skipv, "maxstacksize": 1, "behaviors": [], "texturesByType": tex,
        "attributesByType": attrs, "shapeByType": shapes,
        "storageFlagsByType": {"*-rotten": 1, "*": 32770},
        "transitionablePropsByType": {"*-rotten": [], "*": [{"type": "perish", "freshHours": {"avg": 80}, "transitionHours": {"avg": 24},
            "transitionedStack": {"type": "item", "code": f"{MID}:dead{fam}-{{species}}-{{age}}-1-rotten"}, "transitionRatio": 1}]},
        "creativeinventory": {"general": ["*"], "items": ["*"]},
        "heldTpIdleAnimation": "holdunderarm",
        "guiTransform": {"rotation": {"x": -20, "y": 21, "z": 180}, "origin": {"x": 0.53, "y": 0.35, "z": 0.5}, "scale": 1, "rotate": True},
        "fpHandTransform": {"rotation": {"x": -132, "y": -180, "z": -18}},
        "tpHandTransform": {"translation": {"x": -0.5, "y": -0.3, "z": -0.7}, "rotation": {"x": -89, "y": -12, "z": 3}, "scale": 0.86},
        "groundTransform": {"rotation": {"x": 180, "y": 33, "z": -180}, "origin": {"x": 0.5, "y": 0, "z": 0.5}, "scale": 4.5},
    }
    patches.insert(0, {"op": "replace", "path": "/enabled", "value": True,
                       "file": f"{MID}:itemtypes/butchercreatures/{fam}.json", "dependsOn": [{"modid": modid}]})
    # lang
    lg = {}
    for (sp, age) in sorted(groups):
        nm = None
        for c in groups[(sp, age)]['codes']:
            v = lang.get(f"item-creature-{c}")
            if v: nm = re.sub(r'\s*\(.*\)\s*$', '', v); break
        nm = nm or sp.replace('_', ' ').title()
        lg[f"item-dead{fam}-{sp}-{age}-*"] = f"{nm}{' juvenile' if age == 'baby' else ''} carcass"
        cl = groups[(sp, age)]['cls']
        lg[f"itemdesc-dead{fam}-{sp}-{age}-*"] = {
            'small': 'A light carcass.', 'medium': 'The carcass weighs you down.', 'large': 'The carcass weighs you down a lot.',
            'giant': 'The carcass weighs you down a huge amount.', 'colossal': 'A colossal carcass. You can barely drag it.'}[cl]
    base = os.path.join(ROOT, 'src', 'assets', MID)
    os.makedirs(os.path.join(base, 'itemtypes', 'butchercreatures'), exist_ok=True)
    os.makedirs(os.path.join(base, 'patches', 'lop'), exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'work', 'lang'), exist_ok=True)
    os.makedirs(os.path.join(ROOT, 'work', 'coverage'), exist_ok=True)
    json.dump(itype, open(os.path.join(base, 'itemtypes', 'butchercreatures', f'{fam}.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(patches, open(os.path.join(base, 'patches', 'lop', f'{fam}.json'), 'w', encoding='utf-8'), indent=1)
    json.dump(lg, open(os.path.join(ROOT, 'work', 'lang', f'{fam}.json'), 'w', encoding='utf-8'), indent=1)
    with open(os.path.join(ROOT, 'work', 'coverage', f'{fam}.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['entity', 'file', 'item', 'cls', 'anchor', 'yield_source']); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print(f"{fam}: modid={modid} zip={os.path.basename(zp)} entity_files={len(ents)} variant_rows={len(rows)} species={len(species)} items(species x age)={len(groups)} skip={len(skipv)} patches={len(patches)} classes={dict(Counter(g['cls'] for g in groups.values()))}")

if __name__ == '__main__':
    for f in sys.argv[1:]:
        main(f)
