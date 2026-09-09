from __future__ import annotations
from .evidence import select_evidence,selected_conflicts
from .io import load_json


def _policy_bucket(strictness:str,compatibility:str)->str:
    p=load_json('compatibility/compatibility_rules.json')['strictness_policy'][strictness]
    if compatibility in p.get('allow',[]): return 'allow'
    if compatibility in p.get('warn',[]): return 'warn'
    return 'block_or_resolve'


def _default_action(strictness:str,claim:dict)->dict:
    compat=claim['compatibility']; bucket=_policy_bucket(strictness,compat)
    if bucket=='allow':
        return {'status':'accept','instruction':claim['prompt_implications'][0] if claim.get('prompt_implications') else claim['interpretation']}
    if bucket=='warn':
        return {'status':'qualify','instruction':claim['prompt_implications'][0] if claim.get('prompt_implications') else 'Keep this element qualified rather than presenting it as universal fact.'}
    alt=claim.get('safer_alternatives',[])
    instr='Use a compatible alternative instead of presenting this element as historically secure.'
    if alt: instr += ' Safer alternative: ' + alt[0] + '.'
    return {'status':'adapt','instruction':instr}


def audit_compatibility(spec:dict,claims:list[dict]|None=None)->dict:
    strictness=spec.get('historical',{}).get('strictness','historically_informed')
    claims=claims if claims is not None else select_evidence(spec)
    decisions=[]
    for c in claims:
        action=c.get('mode_actions',{}).get(strictness) or _default_action(strictness,c)
        bucket=_policy_bucket(strictness,c['compatibility'])
        decisions.append({
          'claim_id':c['claim_id'],'claim_version':c['version'],'subject':c['subject'],'compatibility':c['compatibility'],'confidence':c['confidence'],
          'policy_bucket':bucket,'status':action['status'],'instruction':action['instruction'],'source_ids':c.get('source_ids',[]),
          'survival_bias':c.get('survival_bias')
        })
    return {
      'strictness':strictness,
      'summary':{
        'accepted':sum(d['status']=='accept' for d in decisions),
        'qualified':sum(d['status']=='qualify' for d in decisions),
        'adapted':sum(d['status']=='adapt' for d in decisions),
        'rejected':sum(d['status']=='reject' for d in decisions),
        'hybrids':sum(d['status']=='allow_hybrid' for d in decisions),
      },
      'decisions':decisions,
      'claim_relationships':selected_conflicts(claims)
    }


def compatibility_prompt_clauses(audit:dict,claims:list[dict])->list[str]:
    by_id={c['claim_id']:c for c in claims}; out=[]
    for d in audit.get('decisions',[]):
        c=by_id.get(d['claim_id'])
        if not c: continue
        if d['status'] in {'adapt','qualify','reject','allow_hybrid'}:
            out.append(d['instruction'])
        elif c.get('prompt_implications'):
            out.append(c['prompt_implications'][0])
    # keep evidence influence concise and deterministic
    return list(dict.fromkeys(out))[:5]


def survival_bias_clauses(audit:dict)->list[str]:
    return list(dict.fromkeys(d['survival_bias'] for d in audit.get('decisions',[]) if d.get('survival_bias')))[:3]
