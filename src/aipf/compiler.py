from __future__ import annotations
from .io import load_json
from .linting import lint_spec
from .evidence import select_evidence,evidence_snapshot,evidence_explain
from .compatibility import audit_compatibility,compatibility_prompt_clauses,survival_bias_clauses
from .patterns import prompt_pattern_clauses

COMPILER_VERSION='3.2.0'


def _texts(items, limit=3):
    return [x['text'] for x in items[:limit] if isinstance(x,dict) and x.get('text')]


def _sentence(label,value):
    if not value: return None
    return f'{label}: {value}.'


def _load_era_docs(hist):
    registry=load_json('references/eras/registry.json'); path_by_id={x['id']:x['path'] for x in registry['packs']}
    return [load_json(path_by_id[pid]) for pid in hist.get('packs',[]) if pid in path_by_id]


def _era_fragment(pack,art,route,occasion):
    frags=pack.get('prompt_fragments',{})
    if not frags: return None
    preferred=[]; method=art.get('method')
    preferred += {
      'marble_sculpture':['sculpture','bust'], 'bronze_sculpture':['bust','sculpture'], 'carved_stone_relief':['relief','sculpture'],
      'blue_white_ceramic':['ceramic'], 'japanese_woodblock_print':['ukiyoe','woodblock'], 'chinese_ink_painting':['ink'],
      'mineral_pigment_mural':['mural']
    }.get(method,[])
    occ=(occasion or '').casefold()
    if 'lantern' in occ: preferred+=['lantern']
    if route=='historical_portrait': preferred+=['portrait','living','wuxia','court']
    preferred+=list(frags)
    key=next((k for k in preferred if k in frags),None)
    return frags.get(key) if key else None


def compile_result(spec:dict,profile:str|None=None)->dict:
    findings=lint_spec(spec); errors=[f for f in findings if f['level']=='error']
    if errors: raise ValueError('Cannot compile invalid spec: '+'; '.join(f['message'] for f in errors))
    profile=profile or spec['output']['profile']; hist=spec['historical']; art=spec['art']; director=spec.get('director',{})
    claims=select_evidence(spec); snapshot=evidence_snapshot(spec,claims); audit=audit_compatibility(spec,claims); explain=evidence_explain(spec)
    sections=[]
    sections.append(('task',f"Create a coherent visual production from the user's request. Apply explicit locks and the compatibility corrections below; when a compatibility clause adapts a requested element, render the adapted element instead of reasserting the raw request. User request: {spec['request'].rstrip('.')}. Use a {spec['output']['aspect_ratio']} composition."))

    if spec.get('references'):
        role_chunks=[f"{r['id']} supplies {', '.join(r['roles'])} only" for r in spec['references']]
        sections.append(('references','Reference discipline: '+'; '.join(role_chunks)+'. Do not import unassigned identity, body, clothing, objects, layout, or style across references; also do not import unassigned palette, hairstyle, or environment.'))
    imode=spec['identity']['mode']
    if imode!='identity_unlocked':
        modes=load_json('references/core/identity_modes.json')['modes']; sections.append(('identity','Identity: '+modes[imode]))
    bmodes=load_json('references/core/body_modes.json')['modes']; sections.append(('body','Body/presentation: '+bmodes[spec['body_transformation']['mode']]))

    pack_docs=_load_era_docs(hist)
    if pack_docs:
        names=' + '.join(p['name'] for p in pack_docs); ctx=[]
        for key in ['subperiod','region','role','occasion']:
            if hist.get(key): ctx.append(f"{key.replace('_',' ')}: {hist[key]}")
        sections.append(('historical',f"Historical/cultural direction ({hist['strictness']}): {names}. "+('; '.join(ctx)+'.' if ctx else '')))
        base=[p for p in pack_docs if p.get('pack_type') in {'historical_era','site_tradition'}]; overlays=[p for p in pack_docs if p.get('pack_type') in {'genre_overlay','fantasy_overlay'}]
        for p in base:
            anchors=[]
            for field in ['wardrobe','hairstyle_headwear','architecture','textiles_materials','lighting_technology']:
                vals=_texts(p.get(field,[]),1)
                if vals: anchors+=vals
            if anchors: sections.append((f"era_{p['id']}",f"Use {p['name']} anchors selectively: "+'; '.join(anchors[:4])+'.'))
            frag=_era_fragment(p,art,spec.get('route'),hist.get('occasion'))
            if frag: sections.append((f"era_fragment_{p['id']}",frag))
        for p in overlays:
            frag=next(iter(p.get('prompt_fragments',{}).values()),None)
            if frag: sections.append((f"overlay_{p['id']}",'Genre/fantasy overlay: '+frag))
        if hist.get('intentional_hybrids'): sections.append(('hybrids','Intentional adaptation (do not present as documentary fact): '+'; '.join(hist['intentional_hybrids'])+'.'))

    integrity=compatibility_prompt_clauses(audit,claims)
    if integrity:
        lead={
          'strict_reconstruction':'Historical integrity: prioritize strongly evidenced reconstruction and resolve conflicts rather than aestheticizing them away. ',
          'historically_informed':'Historical integrity: preserve strong evidence anchors while allowing clearly bounded interpretation. ',
          'period_drama':'Historical integrity: maintain a coherent period base while treating familiar dramatic conventions as adaptations, not proof. ',
          'fantasy_hybrid':'Historical integrity: allow deliberate hybridization while keeping historical anchors and invented elements visibly distinct. '
        }[hist['strictness']]
        sections.append(('compatibility',lead+' '.join(integrity)))
    survival=survival_bias_clauses(audit)
    if survival:
        state=art.get('artifact_state') or 'living/in-period scene'
        sections.append(('survival_bias',f"Original-vs-surviving appearance ({state}): "+' '.join(survival)))

    method_doc=None
    if art.get('method'):
        artreg=load_json('references/art-methods/registry.json'); apath={x['id']:x['path'] for x in artreg['methods']}[art['method']]; method_doc=load_json(apath)
        core=method_doc['prompt_fragments'].get('core',next(iter(method_doc['prompt_fragments'].values())))
        sections.append(('art_method',f"Art/craft method — {method_doc['name']}: {core}"))
        if art.get('artifact_form'):
            form=load_json('references/artifacts/forms.json')['forms'][art['artifact_form']]; sections.append(('artifact_form',f"Artifact form — {art['artifact_form'].replace('_',' ')}: {form['geometry']}."))
        if art.get('artifact_state'):
            state=load_json('references/artifacts/states.json')['states'][art['artifact_state']]; sections.append(('artifact_state',f"Artifact state — {art['artifact_state'].replace('_',' ')}: {state}"))
        if art.get('variant'): sections.append(('method_variant',f"Method variant: {art['variant']}."))
        sections.append(('material_behavior','Material behavior: '+method_doc['surface_behavior']+' '+method_doc['edge_behavior']))

    order=[('Moment','moment'),('Action','action'),('Gaze','gaze'),('Body weight/support','body_weight'),('Hands','hand_logic'),('Fabric response','fabric_response'),('Prop interaction','prop_interaction'),('Foreground','foreground'),('Midground','midground'),('Background','background'),('Camera/framing','camera'),('Motivated light','light_source'),('Material response','material_response'),('Emotional micro-story','micro_story')]
    selected=order if profile!='compact' else [x for x in order if x[1] in {'moment','action','hand_logic','camera','light_source','micro_story'}]
    director_lines=[]
    for label,key in selected:
        s=_sentence(label,director.get(key))
        if s: director_lines.append(s)
    if director_lines: sections.append(('director',' '.join(director_lines)))

    pattern_clauses,pattern_trace=prompt_pattern_clauses(spec)
    if pattern_clauses:
        sections.append(('validated_visual_patterns','Validated visual mechanisms: '+' '.join(pattern_clauses)))

    avoid=[]
    for p in pack_docs:
        for x in p.get('incompatible_or_anachronistic',[])[:2]:
            if x.get('compatibility') in {'anachronistic','incompatible'}: avoid.append(x['text'])
    if avoid: sections.append(('avoid','Avoid only these likely drift modes: '+'; '.join(dict.fromkeys(avoid))+'.'))
    if method_doc:
        failures=method_doc.get('typical_generation_failures',[])[:3]
        if failures: sections.append(('material_failure_checks','Material failure checks: avoid '+'; '.join(failures)+'.'))
    if spec['output'].get('text_in_image'): sections.append(('visible_text','Render only this exact visible text: '+' | '.join(f'“{t}”' for t in spec['output']['text_in_image'])+'.'))

    if profile=='extended':
        notes=[]
        for p in pack_docs:
            if p.get('strict_reconstruction_note'): notes.append(p['strict_reconstruction_note'])
        if method_doc: notes.append('Material evaluation criteria: '+'; '.join(method_doc.get('evaluation_criteria',[])[:5])+'.')
        if notes: sections.append(('audit_notes','Production audit notes: '+' '.join(notes)))

    prompt='\n\n'.join(text for _,text in sections)
    if profile=='compact': prompt=prompt.replace('\n\n',' ')
    prompt=prompt.strip()+'\n'
    return {'prompt':prompt,'prompt_sections':{k:v for k,v in sections},'compiler_version':COMPILER_VERSION,'pattern_trace':pattern_trace,'evidence_snapshot':snapshot,'compatibility_audit':audit,'evidence_explain':explain,'lint_findings':findings}


def compile_prompt(spec:dict,profile:str|None=None)->str:
    return compile_result(spec,profile)['prompt']
