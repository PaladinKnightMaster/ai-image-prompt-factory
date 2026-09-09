from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from aipf.evidence import claim_paths_for_spec, select_evidence, evidence_snapshot, source_map, selected_conflicts
from aipf.compatibility import audit_compatibility
from aipf.compiler import compile_result
from aipf.corpus import ingest
from aipf.diffing import semantic_diff, prompt_section_diff
from aipf.evaluation import evaluation_template, surgical_revision_plan
from aipf.regression import run_regression, build_baselines, compare_baselines


def load(rel):
    return json.loads((ROOT/rel).read_text(encoding='utf-8'))


def case(rel):
    return load('cases/regression/'+rel+'/case.json')


def test_sources_and_claim_references_exist():
    sources=source_map()
    assert len(sources)>=15
    for path in ROOT.glob('evidence/claims/*.json'):
        for claim in json.loads(path.read_text(encoding='utf-8'))['claims']:
            assert claim['source_ids']
            assert all(sid in sources for sid in claim['source_ids'])
            assert 0 <= claim['confidence'] <= 1
            assert claim['version']


def test_progressive_evidence_loading_is_bounded():
    spec=case('reg-tang-bluewhite-strict-reconstruction')
    paths=claim_paths_for_spec(spec)
    assert len(paths)<=3
    assert 'evidence/claims/tang.json' in paths
    assert 'evidence/claims/edo.json' not in paths


def test_trigger_matching_does_not_leak_tang_cobalt_into_dunhuang():
    spec=case('reg-dunhuang-strict-unbounded')
    ids={x['claim_id'] for x in select_evidence(spec)}
    assert 'tang-cobalt-rare-001' not in ids
    assert 'yuan-bluewhite-flowering-001' not in ids


def test_tang_bluewhite_modes_are_materially_different():
    statuses={}
    prompts={}
    for mode in ['strict-reconstruction','historically-informed','period-drama','fantasy-hybrid']:
        spec=case('reg-tang-bluewhite-'+mode)
        result=compile_result(spec)
        statuses[mode]={d['claim_id']:d['status'] for d in result['compatibility_audit']['decisions']}
        prompts[mode]=result['prompt']
    assert statuses['strict-reconstruction']['tang-cobalt-rare-001']=='adapt'
    assert statuses['historically-informed']['tang-cobalt-rare-001']=='adapt'
    assert statuses['period-drama']['tang-cobalt-rare-001']=='qualify'
    assert statuses['fantasy-hybrid']['tang-cobalt-rare-001']=='allow_hybrid'
    assert len(set(prompts.values()))==4



def test_claim_relationships_are_selected_only_when_claims_cooccur():
    tang=select_evidence(case('reg-tang-bluewhite-strict-reconstruction'))
    ids={r['conflict_id'] for r in selected_conflicts(tang)}
    assert 'tang-bluewhite-chronology-scope-001' in ids
    roman=select_evidence(case('reg-roman-bronze-material'))
    assert 'tang-bluewhite-chronology-scope-001' not in {r['conflict_id'] for r in selected_conflicts(roman)}

def test_evidence_snapshot_is_stable_for_same_spec():
    spec=case('reg-roman-bronze-material')
    a=evidence_snapshot(spec)
    b=evidence_snapshot(deepcopy(spec))
    assert a['snapshot_sha256']==b['snapshot_sha256']
    assert a['claims']


def test_greek_marble_survival_bias_and_state_are_distinct():
    prompts=[]
    for cid in ['reg-greek-marble-newly-created','reg-greek-marble-excavated','reg-greek-marble-museum-conserved']:
        result=compile_result(case(cid))
        assert 'Original-vs-surviving appearance' in result['prompt']
        assert any(d.get('survival_bias') for d in result['compatibility_audit']['decisions'])
        prompts.append(result['prompt'])
    assert len(set(prompts))==3


def test_roman_bronze_is_not_material_substitution():
    result=compile_result(case('reg-roman-bronze-material'))
    p=result['prompt'].casefold()
    assert 'lost-wax' in p or 'casting' in p
    assert 'bronze' in p
    assert 'patina' in p


def test_edo_print_and_ceramic_select_different_material_logic():
    wood=compile_result(case('reg-edo-ukiyoe-process'))['prompt'].casefold()
    ceramic=compile_result(case('reg-edo-ceramic-no-print-leak'))['prompt'].casefold()
    assert 'woodblock' in wood and 'registration' in wood
    assert 'cobalt underglaze' in ceramic
    assert 'art/craft method — japanese woodblock print' not in ceramic


def test_reference_role_isolation_remains_explicit():
    p=compile_result(case('reg-reference-five-role-isolation'))['prompt']
    for role in ['identity','outfit','pose','style','layout']:
        assert f'supplies {role} only' in p
    assert 'Do not import unassigned identity' in p


def test_wuxia_and_xianxia_overlay_behaviors():
    wuxia=compile_result(case('reg-ming-wuxia-overlay'))
    assert 'Genre/fantasy overlay' in wuxia['prompt']
    xianxia=compile_result(case('reg-ming-xianxia-hybrid'))
    assert xianxia['compatibility_audit']['summary']['hybrids']>=1


def test_full_regression_suite_passes():
    r=run_regression()
    assert r['cases']>=18
    assert r['failed']==0, r


def test_baselines_capture_semantic_prompt_and_evidence_hashes():
    b=build_baselines()
    assert len(b['baselines'])==10
    for rec in b['baselines'].values():
        assert len(rec['semantic_spec_sha256'])==64
        assert len(rec['prompt_sha256'])==64
        assert len(rec['evidence_snapshot_sha256'])==64



def test_baseline_compare_detects_no_drift_against_fresh_baseline(tmp_path):
    b=build_baselines(); path=tmp_path/'baseline.json'; path.write_text(json.dumps(b))
    c=compare_baselines(path)
    assert c['ok'] and c['drifted']==0 and c['stable']==10

def test_baseline_compare_detects_prompt_or_spec_drift(tmp_path):
    b=build_baselines(); first=next(iter(b['baselines'].values())); first['prompt_sha256']='0'*64
    path=tmp_path/'baseline.json'; path.write_text(json.dumps(b))
    c=compare_baselines(path)
    assert not c['ok']
    assert any('prompt_sha256' in x['drift_fields'] for x in c['results'])

def test_corpus_ingest_hashes_and_blocks_unknown_license(tmp_path):
    z=tmp_path/'sample.zip'
    fake_jpg=b'\xff\xd8\xff\xd9'
    with ZipFile(z,'w') as out:
        out.writestr('SAMPLE_OUTPUT/A/a.jpg',fake_jpg)
        out.writestr('SAMPLE_OUTPUT/A/b.jpg',fake_jpg)
        out.writestr('notes/readme.md','# x')
    report=ingest(z,tmp_path/'idx')
    assert report['image_assets']==2
    assert report['unique_hashes']==1
    assert report['exact_duplicate_groups']==1
    assert report['public_gallery_eligible']==0
    manifest=json.loads((tmp_path/'idx/image_library_manifest.json').read_text(encoding='utf-8'))
    assert all(a['redistribution_status']=='metadata_only' for a in manifest['assets'])


def test_semantic_diff_reports_paths_not_raw_text_only():
    a={'historical':{'strictness':'strict_reconstruction'},'x':1}
    b={'historical':{'strictness':'historically_informed'},'x':1}
    d=semantic_diff(a,b)
    assert any(x['path']=='historical.strictness' for x in d['changed'])


def test_prompt_section_diff_is_section_aware():
    d=prompt_section_diff({'historical':'A','art_method':'B'},{'historical':'C','art_method':'B','evidence':'D'})
    assert 'historical' in d['changed_sections']
    assert 'evidence' in d['added_sections']
    assert 'art_method' not in d['changed_sections']


def test_evaluation_template_keeps_axes_separate():
    t=evaluation_template('case-x')
    assert set(t['scores'])=={'semantic_compliance','aesthetic_quality','historical_cultural_integrity','art_material_fidelity','identity_fidelity','technical_defects'}
    assert 'wardrobe' in t['subscores']['historical_cultural_integrity']
    assert 'fabrication_marks' in t['subscores']['art_material_fidelity']


def test_surgical_revision_plan_changes_only_failed_dimensions():
    ev=evaluation_template('case-x')
    ev['failure_classes']=['material_failure']
    ev['preserve']=['identity','pose','composition']
    ev['change']=['bronze surface response','patina distribution']
    ev['revision_instruction']='Correct bronze only.'
    p=surgical_revision_plan(ev)
    assert p['preserve']==['identity','pose','composition']
    assert p['change']==['bronze surface response','patina distribution']
    assert p['failure']=='material_failure'
