from __future__ import annotations
from functools import lru_cache
from hashlib import sha256
import json, re
from .io import load_json

WORD_RE=re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*",re.I)
STOPWORDS={'a','an','and','or','the','of','in','on','at','to','for','from','with','as','by','style','period','image','portrait','art'}


def _norm(s:str)->str:
    return re.sub(r"\s+"," ",(s or "").casefold().replace("_"," ")).strip()


def _tokens(s:str)->set[str]:
    return {t for t in WORD_RE.findall(_norm(s)) if t not in STOPWORDS and len(t) > 2}

@lru_cache(maxsize=1)
def source_map()->dict[str,dict]:
    return {x['source_id']:x for x in load_json('evidence/sources/registry.json')['sources']}

@lru_cache(maxsize=1)
def evidence_registry()->dict:
    return load_json('evidence/registry.json')

@lru_cache(maxsize=64)
def _claim_file(path:str)->tuple[dict,...]:
    return tuple(load_json(path)['claims'])


def claim_paths_for_spec(spec:dict)->list[str]:
    reg=evidence_registry(); paths=[]
    selectors={x['selector']:x['path'] for x in reg.get('claim_sets',[])}
    for pid in spec.get('historical',{}).get('packs',[]):
        if pid in selectors: paths.append(selectors[pid])
    method=spec.get('art',{}).get('method')
    for p in reg.get('art_method_claim_sets',{}).get(method,[]): paths.append(p)
    # explicit claims may point outside normal routing; find only if requested.
    explicit=set(spec.get('evidence',{}).get('claim_ids',[]))
    if explicit:
        for row in reg.get('claim_sets',[]):
            if row['path'] not in paths: paths.append(row['path'])
    return list(dict.fromkeys(paths))


def _query_text(spec:dict)->str:
    h=spec.get('historical',{}); a=spec.get('art',{}); d=spec.get('director',{})
    parts=[spec.get('request',''), ' '.join(spec.get('requested_elements',[])), h.get('subperiod') or '',h.get('region') or '',h.get('role') or '',h.get('occasion') or '',a.get('method') or '',a.get('artifact_form') or '',a.get('artifact_state') or '',a.get('variant') or '']
    parts += [str(v) for v in d.values() if v]
    return _norm(' '.join(parts))


def _trigger_match(claim:dict,q:str,q_tokens:set[str])->tuple[bool,int]:
    triggers=claim.get('trigger_keywords',[])
    if not triggers: return bool(claim.get('always_for_context')), 0
    score=0; matched=False
    for t in triggers:
        nt=_norm(t)
        if nt and nt in q:
            matched=True; score += 4 if ' ' in nt or '-' in nt else 2
        else:
            tt=_tokens(t)
            if not tt:
                continue
            ov=len(tt & q_tokens)
            # Avoid evidence leakage from one generic overlapping word. For phrases,
            # require a majority of significant trigger tokens; for single tokens, exact match.
            required=1 if len(tt)==1 else max(2,(len(tt)+1)//2)
            if ov >= required:
                matched=True; score+=ov
    return matched,score


def _context_score(claim:dict,spec:dict)->int:
    ctx=claim.get('context',{}); score=0
    packs=set(spec.get('historical',{}).get('packs',[]))
    cpacks=set(ctx.get('pack_ids',[]))
    if cpacks:
        if cpacks & packs: score+=5
        elif not (cpacks <= packs): return -100
    method=spec.get('art',{}).get('method')
    methods=set(ctx.get('art_methods',[]))
    if methods:
        if method in methods: score+=4
        else: return -100
    state=spec.get('art',{}).get('artifact_state')
    states=set(ctx.get('artifact_states',[]))
    if states:
        if state in states: score+=3
        else: return -100
    sub=_norm(spec.get('historical',{}).get('subperiod') or '')
    if ctx.get('subperiods') and sub:
        if any(_norm(x) in sub or sub in _norm(x) for x in ctx['subperiods']): score+=2
    return score


def select_evidence(spec:dict,limit:int|None=None)->list[dict]:
    q=_query_text(spec); q_tokens=_tokens(q)
    explicit=set(spec.get('evidence',{}).get('claim_ids',[])); excluded=set(spec.get('evidence',{}).get('exclude_claim_ids',[]))
    limit=limit or int(spec.get('evidence',{}).get('max_claims',12))
    candidates=[]
    seen=set()
    for path in claim_paths_for_spec(spec):
        for claim in _claim_file(path):
            cid=claim['claim_id']
            if cid in seen or cid in excluded: continue
            seen.add(cid)
            cs=_context_score(claim,spec)
            if cs < 0 and cid not in explicit: continue
            tm,ts=_trigger_match(claim,q,q_tokens)
            if cid in explicit: tm=True; ts+=20
            if not tm and not claim.get('always_for_context'): continue
            score=cs+ts+int(round(claim.get('confidence',0)*3))
            candidates.append((score,claim))
    candidates.sort(key=lambda x:(-x[0],x[1]['claim_id']))
    return [c for _,c in candidates[:limit]]



@lru_cache(maxsize=1)
def conflict_registry()->dict:
    return load_json('evidence/conflicts/registry.json')


def selected_conflicts(claims:list[dict])->list[dict]:
    ids={c['claim_id'] for c in claims}; out=[]
    for rel in conflict_registry().get('relationships',[]):
        if set(rel.get('claim_ids',[])) <= ids:
            out.append(rel)
    return out

def evidence_snapshot(spec:dict,claims:list[dict]|None=None)->dict:
    claims=claims if claims is not None else select_evidence(spec)
    sources=source_map(); source_ids=[]
    for c in claims:
        source_ids.extend(c.get('source_ids',[]))
    source_ids=list(dict.fromkeys(source_ids))
    relationships=selected_conflicts(claims)
    snap={
      'schema_version':'1.0','skill_version':'3.2.0',
      'claims':[{'claim_id':c['claim_id'],'version':c['version'],'compatibility':c['compatibility'],'confidence':c['confidence'],'source_ids':c['source_ids']} for c in claims],
      'sources':[{'source_id':sid,'title':sources[sid]['title'],'institution':sources[sid].get('institution'),'url':sources[sid]['url'],'evidence_quality':sources[sid]['evidence_quality']} for sid in source_ids if sid in sources],
      'claim_relationships':[{'conflict_id':r['conflict_id'],'version':r['version'],'type':r['type'],'claim_ids':r['claim_ids']} for r in relationships]
    }
    canonical=json.dumps(snap,sort_keys=True,separators=(',',':')).encode()
    snap['snapshot_sha256']=sha256(canonical).hexdigest()
    return snap


def evidence_explain(spec:dict)->dict:
    claims=select_evidence(spec); sm=source_map()
    return {
      'loaded_claim_files':claim_paths_for_spec(spec),
      'claim_relationships':selected_conflicts(claims),
      'selected_claims':[{
        'claim_id':c['claim_id'],'subject':c['subject'],'value':c['value'],'compatibility':c['compatibility'],'confidence':c['confidence'],
        'interpretation':c['interpretation'],'sources':[{'source_id':sid,'title':sm.get(sid,{}).get('title'),'institution':sm.get(sid,{}).get('institution')} for sid in c.get('source_ids',[])]
      } for c in claims],
      'snapshot':evidence_snapshot(spec,claims)
    }
