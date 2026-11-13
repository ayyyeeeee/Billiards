"""Conservative cleanup. Preserve every CSV/video and log every removed file."""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
VIDEO = {'.mkv','.mp4','.avi','.mov','.wmv','.webm','.m4v','.mpeg','.mpg','.mts','.m2ts','.flv','.ts','.vob','.3gp'}
OLD = ['learning_curves_old','learning_curves_revision_preview','learning_curves_robust_preview','learning_curve_tool/component_preview']

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply',action='store_true')
    args=ap.parse_args()
    files=[p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts]
    protected={}
    candidates=[]
    inventory=[]
    for p in files:
        rel=p.relative_to(ROOT).as_posix();st=p.stat()
        inventory.append(dict(path=rel,bytes=st.st_size))
        if p.suffix.lower()=='.csv' or p.suffix.lower() in VIDEO:
            protected[rel]=dict(bytes=st.st_size,mtime_ns=st.st_mtime_ns,
                                sha256=digest(p) if p.suffix.lower()=='.csv' else None)
            continue
        old=any(rel.startswith(folder+'/') for folder in OLD)
        cache='__pycache__' in p.parts and p.suffix.lower() in {'.pyc','.pyo'}
        if old or cache:
            assert ROOT in p.resolve().parents and not p.is_symlink()
            candidates.append(dict(path=rel,bytes=st.st_size,sha256=digest(p),reason='superseded preview/output' if old else 'Python bytecode cache'))
    for pid in range(1,31):
        assert (ROOT/'learning_curves'/f'{pid:02d}.png').exists(), 'Current participant plot missing'
    audit=ROOT/'docs'/'maintenance';audit.mkdir(parents=True,exist_ok=True)
    (audit/'protected_files.json').write_text(json.dumps(protected,indent=2,ensure_ascii=False),encoding='utf-8')
    (audit/'inventory.json').write_text(json.dumps(inventory,indent=2,ensure_ascii=False),encoding='utf-8')
    report=dict(created=datetime.now().isoformat(),applied=False,protected_count=len(protected),candidates=candidates)
    path=audit/'cleanup_report.json'
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    if args.apply:
        for item in candidates:
            p=ROOT/item['path']
            assert p.suffix.lower()!='.csv' and p.suffix.lower() not in VIDEO
            assert ROOT in p.resolve().parents and digest(p)==item['sha256']
            p.unlink()
        folders={p.parent for p in files if '__pycache__' in p.parts}
        folders.update(ROOT/f for f in OLD)
        for folder in sorted(folders,key=lambda p:len(p.parts),reverse=True):
            if folder.exists() and ROOT in folder.resolve().parents and not any(folder.iterdir()): folder.rmdir()
        for rel,original in protected.items():
            p=ROOT/rel;st=p.stat()
            assert st.st_size==original['bytes'] and st.st_mtime_ns==original['mtime_ns'],rel
            if original['sha256']: assert digest(p)==original['sha256'],rel
        report['applied']=True
        report['verification']='All CSV SHA256 unchanged; all video paths, sizes and mtimes unchanged. Videos not rewritten.'
        path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(applied=args.apply,protected=len(protected),removed_or_proposed=len(candidates),bytes=sum(x['bytes'] for x in candidates)),indent=2))

if __name__=='__main__': main()
