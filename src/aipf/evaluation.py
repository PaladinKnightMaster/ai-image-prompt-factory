from __future__ import annotations
from .io import load_json

AXES=['semantic_compliance','aesthetic_quality','historical_cultural_integrity','art_material_fidelity','identity_fidelity','technical_defects']
SUBDIMENSIONS={
 'semantic_compliance':['subject','action','reference_roles','explicit_locks','requested_text'],
 'aesthetic_quality':['visual_hierarchy','coherence','story_moment','light','composition'],
 'historical_cultural_integrity':['wardrobe','hair_headwear','makeup_grooming','props','architecture_furniture','technology_writing','cross_cultural_contamination','evidence_confidence'],
 'art_material_fidelity':['material_identity','fabrication_marks','surface_response','color_behavior','structural_behavior','artifact_form','artifact_state','aging_weathering'],
 'identity_fidelity':['face_identity','age_presentation','distinctive_features','reference_role_isolation'],
 'technical_defects':['anatomy','hands','object_geometry','text_rendering','edge_artifacts','unwanted_duplication']
}


def evaluation_template(case_id:str,spec:dict|None=None)->dict:
    return {'case_id':case_id,'schema_version':'3.2','scores':{a:None for a in AXES},'subscores':{a:{s:None for s in SUBDIMENSIONS[a]} for a in AXES},'observations':[],'failures':[],'failure_classes':[],'preserve':[],'change':[],'revision_instruction':None,'model_metadata':{},'evidence_snapshot_sha256':None,'experiment_subscores':{'pose_mechanic_adherence':None,'hand_logic':None,'prop_interaction':None,'material_response_correctness':None,'composition_depth':None,'lighting_motivation':None,'narrative_clarity':None,'reference_role_isolation':None},'human_review':{'preferred_variant':None,'confidence':None,'notes':None}}


def summarize_evaluation(ev:dict)->dict:
    scores=ev.get('scores',{}); vals=[scores.get(a) for a in AXES if isinstance(scores.get(a),(int,float))]
    return {'average':round(sum(vals)/len(vals),2) if vals else None,'weak_axes':[a for a in AXES if isinstance(scores.get(a),(int,float)) and scores[a]<3.5],'failure_classes':[x.get('class') for x in ev.get('failures',[])]}


def surgical_revision_plan(ev:dict)->dict:
    taxonomy=load_json('evaluation/failure_taxonomy.json')['classes']; preserve=list(ev.get('preserve',[])); changes=[]
    failures=list(ev.get('failures',[]))
    # Accept the compact V3.1 correction shape as well as detailed evaluator failures.
    if not failures and ev.get('failure_classes'):
        for cls in ev.get('failure_classes',[]):
            failures.append({'class':cls,'observation':ev.get('revision_instruction') or 'Observed failure requires targeted correction.','severity':'moderate'})
    for f in failures:
        cls=f['class']; changes.append({'failure':cls,'observation':f.get('observation','Observed failure requires targeted correction.'),'strategy':taxonomy.get(cls,{}).get('revision_strategy','Correct only this observed failure.'),'severity':f.get('severity','moderate')})
    explicit_change=list(ev.get('change',[]))
    plan={'revision_type':'surgical','preserve':preserve,'change':explicit_change or changes,'guardrail':'Do not introduce new wardrobe, identity, cultural, layout, or lighting changes unless required by the listed fixes.'}
    if len(failures)==1:
        plan['failure']=failures[0]['class']
    if ev.get('revision_instruction'):
        plan['revision_instruction']=ev['revision_instruction']
    return plan


def surgical_revision(ev:dict)->str:
    plan=surgical_revision_plan(ev); lines=['Revise the existing image, not the whole concept.']
    if plan['preserve']: lines.append('Preserve exactly what already works: '+'; '.join(plan['preserve'])+'.')
    if plan.get('failure'): lines.append('Failure class: '+plan['failure']+'.')
    for x in plan['change']:
        if isinstance(x,dict): lines.append(f"Fix {x['failure']}: {x['observation']} {x['strategy']}")
        else: lines.append('Change only: '+str(x)+'.')
    if plan.get('revision_instruction'): lines.append(plan['revision_instruction'])
    lines.append(plan['guardrail']); return '\n\n'.join(lines)+'\n'
