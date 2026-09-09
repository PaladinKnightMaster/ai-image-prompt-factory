#!/usr/bin/env python3
"""Package a semantic spec plus optional output/evaluation into a reproducible case folder."""
from __future__ import annotations
from pathlib import Path
import argparse,json,shutil,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from aipf.compiler import compile_result
from aipf.linting import lint_spec


def shafile(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('--group',choices=['golden','public','experimental','regression'],default='experimental'); ap.add_argument('--image'); ap.add_argument('--evaluation'); ap.add_argument('--generation-metadata'); ap.add_argument('--id'); ap.add_argument('--output-publication-status',choices=['private_only','publishable','first_party','generated_by_project'],default='private_only')
    a=ap.parse_args(); spec=json.loads(Path(a.spec).read_text(encoding='utf-8'))
    errors=[x for x in lint_spec(spec) if x['level']=='error']
    if errors: raise SystemExit(json.dumps(errors,ensure_ascii=False,indent=2))
    cid=a.id or spec.get('id')
    if not cid: raise SystemExit('Case spec needs id or --id')
    dest=ROOT/'cases'/a.group/cid; dest.mkdir(parents=True,exist_ok=True); result=compile_result(spec)
    rec=spec.setdefault('case_record',{}); rec.update({'compiled_prompt':'compiled_prompt.md','evidence_snapshot':'evidence_snapshot.json','compatibility_audit':'compatibility_audit.json','compiler_version':'3.2.0','skill_version':'3.2.0'})
    if a.image:
        src=Path(a.image); outname='output'+src.suffix.lower(); shutil.copy2(src,dest/outname); rec['output_image']=outname; rec['output_sha256']=shafile(dest/outname); rec['output_publication_status']=a.output_publication_status
    if a.evaluation: shutil.copy2(a.evaluation,dest/'evaluation.json'); rec['evaluation']='evaluation.json'
    if a.generation_metadata: shutil.copy2(a.generation_metadata,dest/'generation.json'); rec['generation_metadata']='generation.json'
    (dest/'case.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (dest/'compiled_prompt.md').write_text('# Compiled Prompt\n\n'+result['prompt'],encoding='utf-8')
    (dest/'evidence_snapshot.json').write_text(json.dumps(result['evidence_snapshot'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (dest/'compatibility_audit.json').write_text(json.dumps(result['compatibility_audit'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(dest.relative_to(ROOT))
if __name__=='__main__': main()
