from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
from .compiler import compile_result
from .linting import lint_spec
from .io import repo_root


def _hash_obj(obj)->str:
    return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def _hash_file(path:Path)->str|None:
    return sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _check_expectations(spec:dict,result:dict|None,findings:list[dict])->list[str]:
    exp=spec.get('regression_expectations',{}); failures=[]; codes={x.get('code') for x in findings}
    for c in exp.get('finding_codes',[]):
        if c not in codes: failures.append(f'missing expected finding code: {c}')
    for c in exp.get('no_finding_codes',[]):
        if c in codes: failures.append(f'unexpected finding code: {c}')
    if exp.get('expect_compile_error'):
        if result is not None: failures.append('expected compile error but compilation succeeded')
        return failures
    if result is None:
        failures.append('compilation failed unexpectedly'); return failures
    prompt=result['prompt']
    for s in exp.get('prompt_contains',[]):
        if s.casefold() not in prompt.casefold(): failures.append(f'compiled prompt missing: {s}')
    for s in exp.get('prompt_not_contains',[]):
        if s.casefold() in prompt.casefold(): failures.append(f'compiled prompt unexpectedly contains: {s}')
    audit=result.get('compatibility_audit',{}); decisions={x['claim_id']:x for x in audit.get('decisions',[])}
    for cid,status in exp.get('decision_status',{}).items():
        if cid not in decisions: failures.append(f'missing compatibility decision: {cid}')
        elif decisions[cid]['status']!=status: failures.append(f'{cid} status {decisions[cid]["status"]} != {status}')
    loaded=set(result.get('evidence_explain',{}).get('loaded_claim_files',[]))
    if exp.get('max_loaded_claim_files') is not None and len(loaded)>exp['max_loaded_claim_files']:
        failures.append(f'progressive disclosure violated: loaded {len(loaded)} claim files')
    return failures


def run_regression(case_root:str|Path|None=None)->dict:
    root=repo_root(); case_root=Path(case_root) if case_root else root/'cases'/'regression'; cases=sorted(case_root.glob('*/case.json')); results=[]
    for p in cases:
        spec=json.loads(p.read_text(encoding='utf-8')); findings=lint_spec(spec); compiled=None; compile_error=None
        try: compiled=compile_result(spec)
        except Exception as e: compile_error=str(e)
        failures=_check_expectations(spec,compiled,findings)
        expected_error=spec.get('regression_expectations',{}).get('expect_compile_error')
        if expected_error and compile_error is None: failures.append('expected a compile error but none occurred')
        if not expected_error and compile_error: failures.append('unexpected compile error: '+compile_error)
        rec={'id':spec.get('id',p.parent.name),'ok':not failures,'findings':findings,'failures':failures,'compile_error':compile_error}
        if compiled:
            rec.update({
              'prompt_sha256':sha256(compiled['prompt'].encode()).hexdigest(),
              'evidence_snapshot_sha256':compiled['evidence_snapshot']['snapshot_sha256'],
              'evidence_claim_ids':[x['claim_id'] for x in compiled['evidence_explain']['selected_claims']],
              'compatibility_summary':compiled['compatibility_audit']['summary'],
              'compatibility_decisions':[{'claim_id':x['claim_id'],'status':x['status'],'compatibility':x['compatibility']} for x in compiled['compatibility_audit']['decisions']],
              'claim_relationships':[{'conflict_id':x['conflict_id'],'type':x['type']} for x in compiled['compatibility_audit'].get('claim_relationships',[])]
            })
        results.append(rec)
    return {'ok':all(x['ok'] for x in results),'cases':len(results),'passed':sum(x['ok'] for x in results),'failed':sum(not x['ok'] for x in results),'results':results}


def build_baselines(case_root:str|Path|None=None)->dict:
    root=repo_root(); case_root=Path(case_root) if case_root else root/'cases'/'golden'; out={}
    for p in sorted(case_root.glob('*/case.json')):
        spec=json.loads(p.read_text(encoding='utf-8')); result=compile_result(spec); rec=spec.get('case_record',{})
        ev_path=p.parent/(rec.get('evaluation') or 'evaluation.json'); out_path=p.parent/(rec.get('output_image') or 'output.png')
        out[spec['id']]={
          'semantic_spec_sha256':_hash_obj(spec),
          'prompt_sha256':sha256(result['prompt'].encode()).hexdigest(),
          'evidence_snapshot_sha256':result['evidence_snapshot']['snapshot_sha256'],
          'compatibility_sha256':_hash_obj(result['compatibility_audit']),
          'lint_findings_sha256':_hash_obj(result['lint_findings']),
          'evaluation_sha256':_hash_file(ev_path) if rec.get('evaluation') else None,
          'output_sha256':_hash_file(out_path) if rec.get('output_image') else None,
          'compiler_version':'3.2.0','skill_version':'3.2.0','model_alias':rec.get('model_version','gpt-image-2'),
          'model_snapshot':rec.get('model_snapshot','gpt-image-2-2026-04-21')
        }
    return {'version':'1.1.0','baselines':out}


def compare_baselines(baseline_path:str|Path,case_root:str|Path|None=None)->dict:
    baseline=json.loads(Path(baseline_path).read_text(encoding='utf-8')); current=build_baselines(case_root)
    old=baseline.get('baselines',{}); new=current.get('baselines',{}); results=[]
    fields=['semantic_spec_sha256','prompt_sha256','evidence_snapshot_sha256','compatibility_sha256','lint_findings_sha256','evaluation_sha256','output_sha256','compiler_version','skill_version','model_snapshot']
    for cid in sorted(set(old)|set(new)):
        if cid not in old: results.append({'id':cid,'status':'added','drift_fields':fields}); continue
        if cid not in new: results.append({'id':cid,'status':'removed','drift_fields':fields}); continue
        drift=[f for f in fields if old[cid].get(f)!=new[cid].get(f)]
        results.append({'id':cid,'status':'drift' if drift else 'stable','drift_fields':drift})
    return {'ok':not any(x['status'] in {'added','removed','drift'} for x in results),'baseline_version':baseline.get('version'),'cases':len(results),'stable':sum(x['status']=='stable' for x in results),'drifted':sum(x['status']!='stable' for x in results),'results':results}
