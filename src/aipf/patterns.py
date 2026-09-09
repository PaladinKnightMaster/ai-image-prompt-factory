from __future__ import annotations
from functools import lru_cache
from .io import load_json

CONFIDENCE_ORDER={"hypothesis":0,"observed":1,"provisional":2,"supported":3,"strongly_supported":4,"mixed":1,"rejected":-1}

@lru_cache(maxsize=1)
def registry()->dict:
    return load_json('visual-patterns/registry.json')


def all_patterns()->list[dict]:
    return registry().get('patterns',[])


def get_pattern(pattern_id:str)->dict|None:
    return next((p for p in all_patterns() if p['pattern_id']==pattern_id),None)


def validate_pattern_record(p:dict)->list[str]:
    errors=[]
    status=p.get('validation_status','hypothesis')
    eligible=p.get('compiler_usage',{}).get('compiler_eligible',False)
    if eligible and CONFIDENCE_ORDER.get(status,-1)<CONFIDENCE_ORDER['supported']:
        errors.append('compiler_eligible requires supported or strongly_supported status')
    if eligible and not p.get('mechanism',{}).get('instruction'):
        errors.append('compiler_eligible pattern requires an instruction')
    if status in {'supported','strongly_supported'} and not p.get('evidence',{}).get('validation_basis'):
        errors.append('supported pattern requires validation_basis')
    return errors


def select_patterns(spec:dict, *, compiler_only:bool=True, limit:int=4)->list[dict]:
    vp=spec.get('visual_patterns',{})
    requested=vp.get('include',[])
    excluded=set(vp.get('exclude',[]))
    enabled=bool(vp.get('enable_validated',False) or requested)
    if compiler_only and not enabled:
        return []
    route=spec.get('route')
    text=(spec.get('request','')+' '+str(spec.get('director',{}))).casefold()
    scored=[]
    for p in all_patterns():
        if p['pattern_id'] in excluded: continue
        if compiler_only and not p.get('compiler_usage',{}).get('compiler_eligible',False): continue
        score=0
        if requested and not vp.get('enable_validated',False):
            if p['pattern_id'] not in requested: continue
            score=100
        else:
            if p['pattern_id'] in requested: score+=100
            routes=p.get('compiler_usage',{}).get('routes',[])
            if route and (not routes or route in routes): score+=4
            for trig in p.get('retrieval_terms',[]):
                if trig.casefold() in text: score+=2
        if score>0: scored.append((score,p['pattern_id'],p))
    scored.sort(key=lambda x:(-x[0],x[1]))
    return [p for _,_,p in scored[:limit]]


def prompt_pattern_clauses(spec:dict)->tuple[list[str],list[dict]]:
    clauses=[]; trace=[]
    for p in select_patterns(spec,compiler_only=True):
        instruction=p['mechanism']['instruction'].rstrip('.')+'.'
        clauses.append(instruction)
        trace.append({
            'pattern_id':p['pattern_id'],
            'version':p['version'],
            'validation_status':p['validation_status'],
            'clause':instruction,
            'source':'visual_pattern_registry'
        })
    return clauses,trace
