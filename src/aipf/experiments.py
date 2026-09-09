from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json,re
from .io import repo_root,load_json
from .prompt_mechanisms import decompose_prompt


def load_experiment(experiment_id_or_path:str|Path)->dict:
    p=Path(experiment_id_or_path)
    if not p.exists(): p=repo_root()/'experiments'/'definitions'/f'{experiment_id_or_path}.json'
    return json.loads(p.read_text(encoding='utf-8'))


def apply_ablation(prompt:str,variant:dict)->str:
    mode=variant.get('operation')
    if mode=='remove_regex':
        return re.sub(variant['pattern'],'',prompt,flags=re.I|re.M).replace('  ',' ').strip()
    if mode=='replace_regex':
        return re.sub(variant['pattern'],variant.get('replacement',''),prompt,flags=re.I|re.M).strip()
    if mode=='append':
        return (prompt.rstrip()+' '+variant['text'].strip()).strip()
    if mode=='replace_literal':
        old=variant['old']; new=variant.get('new','')
        if old not in prompt: raise ValueError(f'ablation literal not found: {old}')
        return prompt.replace(old,new)
    if mode=='identity': return prompt
    raise ValueError(f'unknown experiment operation: {mode}')


def plan_experiment(exp:dict)->dict:
    base=exp['baseline_prompt']
    variants=[]
    for v in exp['variants']:
        out=apply_ablation(base,v)
        variants.append({**v,'prompt':out,'decomposition':decompose_prompt(out)})
    return {
      'experiment_id':exp['experiment_id'],'version':exp['version'],'hypothesis':exp['hypothesis'],
      'status':exp.get('status','planned'),'model_target':exp.get('model_target','gpt-image-2'),
      'control_prompt':base,'variants':variants,
      'preserved_dimensions':exp.get('preserved_dimensions',[]),'evaluation_dimensions':exp.get('evaluation_dimensions',[])
    }


def validate_single_factor(exp:dict)->list[str]:
    errors=[]; base=exp['baseline_prompt']
    for v in exp['variants']:
        if v.get('id')=='control' or v.get('operation')=='identity': continue
        try: out=apply_ablation(base,v)
        except Exception as e: errors.append(f"{v.get('id')}: {e}"); continue
        if out==base: errors.append(f"{v.get('id')}: variant made no change")
        if not v.get('factor'): errors.append(f"{v.get('id')}: missing factor")
    return errors


def experiment_report(exp:dict,results:dict|None=None)->dict:
    plan=plan_experiment(exp); results=results or {}
    executed=bool(results.get('outputs'))
    return {
      'experiment_id':exp['experiment_id'],'hypothesis':exp['hypothesis'],'execution_status':'executed' if executed else 'planned_not_executed',
      'reason_if_not_executed':None if executed else 'No controlled GPT Image 2 generation run is recorded for this release.',
      'plan':plan,'results':results,'conclusion':results.get('conclusion','unverified') if executed else 'unverified',
      'pattern_confidence_update':results.get('pattern_confidence_update') if executed else None
    }


def experiment_inventory()->dict:
    root=repo_root()/'experiments'/'definitions'; exps=[]
    for p in sorted(root.glob('*.json')):
        exp=json.loads(p.read_text(encoding='utf-8'))
        exps.append({'experiment_id':exp['experiment_id'],'status':exp.get('status','planned'),'hypothesis':exp['hypothesis'],'single_factor_errors':validate_single_factor(exp)})
    return {'count':len(exps),'executed':sum(x['status']=='executed' for x in exps),'planned':sum(x['status']!='executed' for x in exps),'experiments':exps}
