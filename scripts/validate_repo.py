#!/usr/bin/env python3
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json,sys
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from aipf.io import load_json
from aipf.linting import lint_spec
from aipf.compiler import compile_result
from aipf.regression import run_regression,build_baselines
from aipf.evidence import source_map


def validate_obj(obj,schema,label,errors):
    for e in Draft202012Validator(schema).iter_errors(obj):
        errors.append(f'{label}: {e.message}')


def check_json_files(errors):
    count=0
    for p in ROOT.rglob('*.json'):
        try: json.loads(p.read_text(encoding='utf-8')); count+=1
        except Exception as e: errors.append(f'invalid JSON {p.relative_to(ROOT)}: {e}')
    return count


def check_schemas(errors):
    for p in sorted((ROOT/'data/schemas').glob('*.json')):
        try:
            Draft202012Validator.check_schema(json.loads(p.read_text(encoding='utf-8')))
        except Exception as e:
            errors.append(f'invalid schema {p.relative_to(ROOT)}: {e}')


def check_registry_targets(errors):
    for regrel in ['data/registry.json','references/eras/registry.json','references/art-methods/registry.json','references/routes/registry.json','evidence/registry.json']:
        obj=load_json(regrel)
        def walk(x):
            if isinstance(x,dict):
                for v in x.values(): walk(v)
            elif isinstance(x,list):
                for v in x: walk(v)
            elif isinstance(x,str) and x.endswith('.json') and '/' in x:
                if not (ROOT/x).exists(): errors.append(f'{regrel}: missing target {x}')
        walk(obj)


def check_modules(errors):
    pairs=[
      ('references/eras/registry.json','data/schemas/era_pack.schema.json','packs'),
      ('references/art-methods/registry.json','data/schemas/art_method.schema.json','methods')]
    for regrel,schemarel,key in pairs:
        schema=load_json(schemarel)
        for row in load_json(regrel)[key]:
            obj=load_json(row['path']); validate_obj(obj,schema,row['path'],errors)
            if not obj.get('version'): errors.append(f"{row['path']}: missing knowledge version")


def check_evidence(errors):
    source_schema=load_json('data/schemas/source.schema.json')
    claim_schema=load_json('data/schemas/evidence_claim.schema.json')
    sources=load_json('evidence/sources/registry.json').get('sources',[])
    source_ids=set()
    for s in sources:
        validate_obj(s,source_schema,f"source:{s.get('source_id')}",errors)
        if s.get('source_id') in source_ids: errors.append(f"duplicate source id: {s.get('source_id')}")
        source_ids.add(s.get('source_id'))
    claims=0; claim_ids=set()
    for p in sorted((ROOT/'evidence/claims').glob('*.json')):
        obj=json.loads(p.read_text(encoding='utf-8'))
        if not obj.get('version'): errors.append(f'{p.relative_to(ROOT)}: missing claim-set version')
        for c in obj.get('claims',[]):
            claims+=1; validate_obj(c,claim_schema,f"claim:{c.get('claim_id')}",errors)
            if c.get('claim_id') in claim_ids: errors.append(f"duplicate claim id: {c.get('claim_id')}")
            claim_ids.add(c.get('claim_id'))
            for sid in c.get('source_ids',[]):
                if sid not in source_ids: errors.append(f"claim {c.get('claim_id')} references missing source {sid}")
    rel_schema=load_json('data/schemas/evidence_conflict.schema.json'); rels=load_json('evidence/conflicts/registry.json').get('relationships',[])
    for rel in rels:
        validate_obj(rel,rel_schema,f"relationship:{rel.get('conflict_id')}",errors)
        for cid in rel.get('claim_ids',[]):
            if cid not in claim_ids: errors.append(f"relationship {rel.get('conflict_id')} references missing claim {cid}")
    return len(sources),claims,len(rels)


def case_schema():
    req=load_json('data/schemas/request.schema.json')
    case=deepcopy(load_json('data/schemas/case.schema.json'))
    # Resolve the local request ref in memory so validation never needs network/file URI resolution.
    case['allOf']=[req if x.get('$ref')=='request.schema.json' else x for x in case.get('allOf',[])]
    return case


def check_cases(errors):
    schema=case_schema(); golden=sorted((ROOT/'cases/golden').glob('*/case.json')); compiled=0
    if len(golden)!=10: errors.append(f'expected 10 golden cases, found {len(golden)}')
    for p in golden:
        spec=json.loads(p.read_text(encoding='utf-8')); validate_obj(spec,schema,str(p.relative_to(ROOT)),errors)
        errs=[x for x in lint_spec(spec) if x['level']=='error']
        for f in errs: errors.append(f"{p.relative_to(ROOT)} [{f['code']}]: {f['message']}")
        try:
            r=compile_result(spec)
            if len(r['prompt'])<300: errors.append(f'compiled prompt suspiciously short: {p.relative_to(ROOT)}')
            (p.parent/'compiled_prompt.md').write_text('# Compiled Prompt\n\n'+r['prompt'],encoding='utf-8')
            (p.parent/'evidence_snapshot.json').write_text(json.dumps(r['evidence_snapshot'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            (p.parent/'compatibility_audit.json').write_text(json.dumps(r['compatibility_audit'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            compiled+=1
        except Exception as e: errors.append(f'compile failure {p.relative_to(ROOT)}: {e}')
    regression=sorted((ROOT/'cases/regression').glob('*/case.json'))
    for p in regression:
        validate_obj(json.loads(p.read_text(encoding='utf-8')),schema,str(p.relative_to(ROOT)),errors)
    return len(golden),compiled,len(regression)


def check_corpus(errors):
    manifest=ROOT/'corpus/indexes/image_library_manifest.json'
    if not manifest.exists():
        errors.append('missing corpus/indexes/image_library_manifest.json'); return 0,0,0
    obj=json.loads(manifest.read_text(encoding='utf-8')); schema=load_json('data/schemas/corpus_asset.schema.json')
    hashes=set(); dup_extra=0
    for a in obj.get('assets',[]):
        validate_obj(a,schema,f"corpus:{a.get('relative_path')}",errors)
        if a.get('redistribution_status')=='publishable' and a.get('license_status')=='unknown_license':
            errors.append(f"corpus asset illegally publishable with unknown license: {a.get('relative_path')}")
        if a.get('sha256') in hashes: dup_extra+=1
        hashes.add(a.get('sha256'))
    return len(obj.get('assets',[])),len(hashes),dup_extra


def check_evaluation_example(errors):
    validate_obj(load_json('evaluation/example_evaluation.json'),load_json('data/schemas/evaluation.schema.json'),'evaluation/example_evaluation.json',errors)


def check_required(errors):
    required=[
      'README.md','SKILL.md','manifest.json','evidence/registry.json','evidence/sources/registry.json',
      'visual-patterns/registry.json','experiments/README.md','benchmarks/README.md','internal-gallery/generate_gallery.py',
      'corpus/indexes/ingestion_report.json','corpus/indexes/prompt_index.json','corpus/indexes/distillation_report.json',
      'regression/reports/latest.json','regression/baselines/golden_baselines.json',
      'docs/ADR-0002-v3.1-evidence-regression.md','docs/ADR-0003-v3.2-visual-intelligence-lab.md',
      'docs/EVIDENCE_MODEL.md','docs/COMPATIBILITY_GRAPH.md','docs/SAMPLE_INGESTION.md','docs/REGRESSION_TESTING.md',
      'docs/EVALUATION_V3_1.md','docs/LICENSING_AND_PROVENANCE.md','docs/MIGRATION_V3_0_TO_V3_1.md',
      'docs/INTERNAL_CORPUS.md','docs/INTERNAL_GALLERY.md','docs/PROMPT_MECHANISM_MODEL.md',
      'docs/VISUAL_PATTERN_REGISTRY.md','docs/EXPERIMENT_LAB.md','docs/ABLATION_TESTING.md',
      'docs/FIRST_PARTY_BENCHMARKS.md','docs/V3_1_TO_V3_2_MIGRATION.md','docs/MANUAL_INSPECTION_V3_2.md',
      'docs/RESEARCH_NOTES_V3_2.md','docs/VALIDATION_REPORT_V3_2.md','docs/V3_3_ROADMAP.md']
    for rel in required:
        if not (ROOT/rel).exists(): errors.append(f'missing required file: {rel}')



def check_v32_artifacts(errors):
    from aipf.patterns import all_patterns,validate_pattern_record
    from aipf.experiments import experiment_inventory
    from aipf.benchmarks import benchmark_report
    vp_schema=load_json('data/schemas/visual_pattern.schema.json')
    pats=all_patterns()
    for rec in pats:
        validate_obj(rec,vp_schema,f"pattern:{rec.get('pattern_id')}",errors)
        for e in validate_pattern_record(rec): errors.append(f"pattern {rec.get('pattern_id')}: {e}")
    exp_schema=load_json('data/schemas/experiment.schema.json')
    for ep in sorted((ROOT/'experiments/definitions').glob('*.json')):
        validate_obj(json.loads(ep.read_text(encoding='utf-8')),exp_schema,str(ep.relative_to(ROOT)),errors)
    inv=experiment_inventory()
    for e in inv['experiments']:
        for err in e['single_factor_errors']: errors.append(f"experiment {e['experiment_id']}: {err}")
    bench_schema=load_json('data/schemas/benchmark.schema.json')
    for bp in sorted((ROOT/'benchmarks/candidates').glob('*.json'))+sorted((ROOT/'benchmarks/golden').glob('*.json')):
        validate_obj(json.loads(bp.read_text(encoding='utf-8')),bench_schema,str(bp.relative_to(ROOT)),errors)
    br=benchmark_report()
    # Hard public/internal boundary: no collected raster assets in the
    # distributable source tree. Ignore local test/build environments because
    # tests may intentionally create temporary image fixtures.
    ignored_parts={'.git','.venv','.pytest_tmp','.pytest_cache','__pycache__','dist','build'}
    raw=[]
    for x in ROOT.rglob('*'):
        if not x.is_file() or x.suffix.lower() not in {'.jpg','.jpeg','.png','.webp'}:
            continue
        rel=x.relative_to(ROOT)
        if any(part in ignored_parts or part.endswith('.egg-info') for part in rel.parts):
            continue
        if rel.as_posix().startswith('website/generated/'):
            continue
        raw.append(x)
    if raw: errors.append('raw internal/public raster assets unexpectedly present: '+', '.join(str(x.relative_to(ROOT)) for x in raw[:5]))
    return len(pats),sum(x.get('compiler_usage',{}).get('compiler_eligible',False) for x in pats),inv['count'],inv['executed'],br['candidate_count'],br['golden_count']

def main():
    errors=[]
    json_count=check_json_files(errors); check_schemas(errors); check_registry_targets(errors); check_modules(errors); check_evaluation_example(errors)
    sources,claims,relationships=check_evidence(errors)
    golden,compiled,reg_cases=check_cases(errors)
    corpus_assets,unique_hashes,dup_extra=check_corpus(errors)
    patterns,eligible_patterns,experiments,executed_experiments,benchmark_candidates,benchmark_golden=check_v32_artifacts(errors)
    reg=run_regression()
    if not reg['ok']:
        for x in reg['results']:
            if not x['ok']: errors.append(f"regression {x['id']}: {'; '.join(x['failures'])}")
    # Refresh reproducibility artifacts after compilation.
    (ROOT/'regression/reports/latest.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    baselines=build_baselines(); (ROOT/'regression/baselines/golden_baselines.json').write_text(json.dumps(baselines,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    check_required(errors)
    result={
      'ok':not errors,'skill_version':'3.2.0','compiler_version':'3.2.0','json_files':json_count,
      'era_packs':len(load_json('references/eras/registry.json')['packs']),'art_methods':len(load_json('references/art-methods/registry.json')['methods']),
      'evidence_sources':sources,'evidence_claims':claims,'evidence_relationships':relationships,'golden_cases':golden,'compiled_golden_cases':compiled,
      'regression_cases':reg_cases,'regression_passed':reg['passed'],'regression_failed':reg['failed'],
      'corpus_assets':corpus_assets,'corpus_unique_hashes':unique_hashes,'corpus_duplicate_extra_files':dup_extra,
      'visual_patterns':patterns,'compiler_eligible_patterns':eligible_patterns,'experiment_definitions':experiments,'executed_experiments':executed_experiments,'benchmark_candidates':benchmark_candidates,'benchmark_golden':benchmark_golden,
      'errors':errors}
    print(json.dumps(result,ensure_ascii=False,indent=2)); raise SystemExit(0 if not errors else 1)

if __name__=='__main__': main()
