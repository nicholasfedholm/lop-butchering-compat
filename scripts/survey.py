import sys,csv,zipfile,glob,os,collections
sys.path.insert(0,os.path.dirname(__file__))
import lopresolve as L
M=os.environ.get('VS_MODS') or os.path.join(os.environ.get('APPDATA',''),'VintagestoryData','Mods')
rows=[]
for zp in sorted(glob.glob(M+'/LoP-*.zip')+glob.glob(M+'/lop-ceratops-*.zip')):
    z=zipfile.ZipFile(zp)
    ents=[n for n in z.namelist() if '/entities/' in n and n.endswith('.json')]
    for e in ents:
        base=os.path.basename(e)[:-5]
        if base in ('egg','nest','lure','dino-hitch') or 'hitch' in base or 'lure' in base or 'nest' in base or 'egg' in base: continue
        ent=L.load_entity(zp,e)
        for code,vg in L.variants(ent):
            r=L.solve(ent,code); h=L.harvest(r)
            meat=0; drops=[]
            if h:
                for d in h.get('drops',[]):
                    q=(d.get('quantity') or {}).get('avg') or 0
                    drops.append(f"{d.get('code')}:{q}")
                    if 'meat' in str(d.get('code')) or 'fish' in str(d.get('code')): meat+=q
            dd=[b for b in r.get('server',{}).get('behaviors',[]) if b.get('code')=='deaddecay']
            hb=r.get('hitBoxSize') or {}
            rows.append(dict(zip=os.path.basename(zp),file=e,code=code,age=vg.get('age',''),meat=meat,hbx=hb.get('x'),hby=hb.get('y'),harv=bool(h),alt=L.tex_alternates(r),decayed=(dd[0].get('decayedBlock') if dd else None),drops=' '.join(drops),habitat=r.get('habitat','')))
w=csv.DictWriter(open('work/survey.csv','w',newline='',encoding='utf-8'),fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
agg=collections.defaultdict(list)
for r in rows: agg[(r['zip'][:22],r['age'] or '-')].append(r)
for k,v in sorted(agg.items()):
    ms=[x['meat'] for x in v]; hs=[x['hby'] or 0 for x in v]
    print(f"{k[0]:22} {k[1]:6} n={len(v):4} meat {min(ms):5}-{max(ms):5} hby {min(hs)}-{max(hs)} noharv={sum(not x['harv'] for x in v)} alt<= {max(x['alt'] for x in v)} decayed={sorted(set(str(x['decayed']) for x in v))[:2]}")
