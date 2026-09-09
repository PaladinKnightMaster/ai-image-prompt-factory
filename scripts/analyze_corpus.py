#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from aipf.prompt_mechanisms import quality_audit

def main():
    idx=json.loads((ROOT/'corpus/indexes/prompt_index.json').read_text(encoding='utf-8'))['prompt_records']
    cats={}; methods={}; low=[]
    for p in idx:
        d=p['decomposition']
        for k,v in d.get('category_counts',{}).items(): cats[k]=cats.get(k,0)+v
        for m in d.get('prompt_methods',[]): methods[m]=methods.get(m,0)+1
        a=quality_audit(p['prompt_text'])
        if a['issues']: low.append({'prompt_id':p['prompt_id'],'issues':a['issues']})
    obs=json.loads((ROOT/'corpus/indexes/pattern_observations.json').read_text(encoding='utf-8'))['observations']
    report={'prompt_records':len(idx),'category_clause_counts':dict(sorted(cats.items(),key=lambda x:-x[1])),'prompt_method_counts':dict(sorted(methods.items(),key=lambda x:-x[1])),'prompts_with_quality_audit_findings':len(low),'sample_quality_findings':low[:20],'pattern_observation_types':len(obs)}
    (ROOT/'corpus/indexes/distillation_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
