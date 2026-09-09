from __future__ import annotations
from pathlib import Path
import json
from .io import repo_root


def list_benchmarks(kind:str='candidates')->list[dict]:
    root=repo_root()/'benchmarks'/kind
    out=[]
    if not root.exists(): return out
    for p in sorted(root.glob('*.json')):
        out.append(json.loads(p.read_text(encoding='utf-8')))
    return out


def benchmark_report()->dict:
    candidates=list_benchmarks('candidates'); golden=list_benchmarks('golden')
    return {
      'candidate_count':len(candidates),'golden_count':len(golden),
      'generated_candidates':sum(bool(x.get('generation',{}).get('output_image')) for x in candidates),
      'promotion_rule':'Golden requires generated output, recorded metadata, evaluation, and human approval.',
      'candidates':[{'benchmark_id':x['benchmark_id'],'status':x.get('status'),'category':x.get('category'),'generation_status':x.get('generation',{}).get('status','not_generated')} for x in candidates]
    }
