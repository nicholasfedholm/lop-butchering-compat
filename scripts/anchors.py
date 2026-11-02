import pyjson5,glob,os,sys
root=sys.argv[1]
for f in sorted(glob.glob(root+'/itemtypes/butchercreatures/*.json')+glob.glob(root+'/itemtypes/butchercreatures/*/*.json')):
    n=os.path.relpath(f,root+'/itemtypes/butchercreatures')
    if not any(k in n for k in ('pig','deer','moose','sheep','goat','chicken','hare','bear','elephant','rhino','wolf','fox')): continue
    j=pyjson5.loads(open(f,encoding='utf-8-sig').read())
    for k,a in (j.get('attributesByType') or {}).items():
        br=' '.join(f"{r['code'].split(':')[-1]}:{r['quantity']['avg']}" for r in a.get('butcheringRewards',[]))
        sr=' '.join(f"{r['code'].split(':')[-1]}:{r['quantity']['avg']}" for r in a.get('skinningRewards',[]))
        hs=(a.get('hangingShape') or {}).get('base','').split('/')[-1]
        print(f"{k[:44]:44} m={a.get('mass')} bl={a.get('bloodAmount')} wl={a.get('butcheringWorkLoad')} hang={hs} B[{br}] S[{sr}]")
