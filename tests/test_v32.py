from pathlib import Path
import json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from aipf.corpus import COLLECTIONS, ingest
from aipf.prompt_mechanisms import decompose_prompt,quality_audit
from aipf.patterns import all_patterns,select_patterns,validate_pattern_record
from aipf.experiments import load_experiment,plan_experiment,validate_single_factor,experiment_inventory
from aipf.benchmarks import benchmark_report
from aipf.compiler import compile_result

def load(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))

def test_collection_mappings_are_correct():
    assert COLLECTIONS['LCC']['collection_name']=='Larus Canus Collection'
    assert COLLECTIONS['LCC']['creator_url']=='https://x.com/MrLarus'
    assert COLLECTIONS['LAC']['collection_name']=='Liyue AI Collection'
    assert COLLECTIONS['LAC']['creator_url']=='https://x.com/liyue_ai'

def test_real_corpus_index_counts_and_internal_boundary():
    r=load('corpus/indexes/ingestion_report.json')
    assert r['image_assets']==606 and r['unique_hashes']==587 and r['exact_duplicate_extra_files']==19
    assert r['collections']=={'APC':100,'FSC':24,'GAC':33,'LAC':71,'LCC':378}
    assert r['internal_only_assets']==606 and r['public_gallery_eligible']==0

def test_prompt_index_and_associations_exist():
    r=load('corpus/indexes/ingestion_report.json'); assert r['prompt_records']>=150
    a=r['image_prompt_associations']; assert a['exact_section']+a['probable_section']>=400

def test_decomposition_is_functional_not_sentence_only():
    d=decompose_prompt('She stands with most weight on the rear leg. Soft window light. 8K masterpiece.')
    cats={c for x in d['clauses'] for c in x['categories']}
    assert {'pose','body_mechanics','lighting','quality_low_signal'} <= cats

def test_low_signal_audit_marks_not_blindly_removes():
    a=quality_audit('Hasselblad camera, 8K masterpiece, ultra-detailed portrait.')
    names={x['term_class'] for x in a['decomposition']['low_signal']['findings']}
    assert 'camera_brand' in names and '8k_16k_hype' in names

def test_pattern_registry_size_and_epistemic_rules():
    pats=all_patterns(); assert 20 <= len(pats) <= 40
    assert all(not validate_pattern_record(p) for p in pats)
    assert any(p['validation_status']=='observed' for p in pats)
    assert any(p['compiler_usage']['compiler_eligible'] for p in pats)

def test_unvalidated_patterns_do_not_auto_enter_compiler():
    spec=load('cases/golden/04-tang-court-lantern/case.json'); spec['visual_patterns']={'include':['pose-explicit-weight-distribution']}
    assert select_patterns(spec,compiler_only=True)==[]

def test_supported_pattern_can_be_explicitly_used():
    spec=load('cases/golden/04-tang-court-lantern/case.json'); spec['visual_patterns']={'include':['interaction-explicit-prop']}
    r=compile_result(spec)
    assert any(x['pattern_id']=='interaction-explicit-prop' for x in r['pattern_trace'])
    assert 'Validated visual mechanisms:' in r['prompt']

def test_experiments_are_planned_not_faked():
    inv=experiment_inventory(); assert inv['count']>=10 and inv['executed']==0
    assert all(not x['single_factor_errors'] for x in inv['experiments'])

def test_ablation_changes_only_declared_factor_mechanically():
    e=load_experiment('EXP-007'); p=plan_experiment(e)
    assert p['variants'][0]['prompt']==p['control_prompt']
    assert p['variants'][1]['prompt']!=p['control_prompt']
    assert '8K masterpiece' not in p['variants'][1]['prompt']

def test_benchmark_candidates_not_promoted_without_outputs():
    r=benchmark_report(); assert r['candidate_count']>=20 and r['golden_count']==0 and r['generated_candidates']==0

def test_public_repo_contains_no_raw_internal_images():
    imgs=[p for p in ROOT.rglob('*') if p.suffix.lower() in {'.jpg','.jpeg','.png','.webp'}]
    assert not [p for p in imgs if 'website/generated' not in str(p)]
