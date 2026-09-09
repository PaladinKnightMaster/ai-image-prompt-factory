from __future__ import annotations
from hashlib import sha256
import json,re


def _flatten(obj,prefix=''):
    out={}
    if isinstance(obj,dict):
        for k,v in obj.items(): out.update(_flatten(v,f'{prefix}.{k}' if prefix else k))
    elif isinstance(obj,list): out[prefix]=obj
    else: out[prefix]=obj
    return out


def semantic_diff(old:dict,new:dict,ignore_paths:tuple[str,...]=('case_record.compiled_prompt',))->dict:
    a=_flatten(old); b=_flatten(new); changes=[]
    for p in sorted(set(a)|set(b)):
        if any(p.startswith(x) for x in ignore_paths): continue
        if p not in a: changes.append({'path':p,'type':'added','new':b[p]})
        elif p not in b: changes.append({'path':p,'type':'removed','old':a[p]})
        elif a[p]!=b[p]: changes.append({'path':p,'type':'changed','old':a[p],'new':b[p]})
    grouped={
      'added':[x for x in changes if x['type']=='added'],
      'removed':[x for x in changes if x['type']=='removed'],
      'changed':[x for x in changes if x['type']=='changed'],
    }
    return {'change_count':len(changes),'changes':changes,**grouped}


def prompt_sections(prompt:str)->dict[str,str]:
    chunks=[x.strip() for x in re.split(r'\n\s*\n',prompt.strip()) if x.strip()]
    out={}
    for i,c in enumerate(chunks):
        head=c.split(':',1)[0].strip() if ':' in c.split('\n',1)[0] else f'section_{i+1}'
        key=head.casefold().replace(' ','_')
        if key in out: key=f'{key}_{i+1}'
        out[key]=c
    return out


def prompt_semantic_diff(old:str,new:str)->dict:
    a=prompt_sections(old); b=prompt_sections(new); changes=[]
    for k in sorted(set(a)|set(b)):
        if k not in a: changes.append({'section':k,'type':'added','new':b[k]})
        elif k not in b: changes.append({'section':k,'type':'removed','old':a[k]})
        elif a[k]!=b[k]: changes.append({'section':k,'type':'changed','old':a[k],'new':b[k]})
    return {'old_sha256':sha256(old.encode()).hexdigest(),'new_sha256':sha256(new.encode()).hexdigest(),'change_count':len(changes),'changes':changes}


def prompt_section_diff(old_sections:dict[str,str],new_sections:dict[str,str])->dict:
    added={k:new_sections[k] for k in new_sections.keys()-old_sections.keys()}
    removed={k:old_sections[k] for k in old_sections.keys()-new_sections.keys()}
    changed={k:{'old':old_sections[k],'new':new_sections[k]} for k in old_sections.keys() & new_sections.keys() if old_sections[k]!=new_sections[k]}
    return {'added_sections':added,'removed_sections':removed,'changed_sections':changed,'change_count':len(added)+len(removed)+len(changed)}


def compile_trace_diff(old:dict,new:dict)->dict:
    """Semantic compiler diff including section and VisualPattern provenance changes."""
    sections=prompt_section_diff(old.get('prompt_sections',{}),new.get('prompt_sections',{}))
    a={x['pattern_id']:x for x in old.get('pattern_trace',[])}; b={x['pattern_id']:x for x in new.get('pattern_trace',[])}
    return {
      'prompt_sections':sections,
      'patterns_added':[b[k] for k in sorted(b.keys()-a.keys())],
      'patterns_removed':[a[k] for k in sorted(a.keys()-b.keys())],
      'patterns_changed':[{'pattern_id':k,'old':a[k],'new':b[k]} for k in sorted(a.keys() & b.keys()) if a[k]!=b[k]],
      'evidence_snapshot_changed':old.get('evidence_snapshot',{}).get('snapshot_sha256')!=new.get('evidence_snapshot',{}).get('snapshot_sha256')
    }
