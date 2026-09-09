from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'src'))

from aipf.classifier import classify
from aipf.compiler import compile_prompt
from aipf.linting import lint_spec, lint_prompt
from aipf.evaluation import surgical_revision


def load(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))

def golden(): return sorted((ROOT/'cases/golden').glob('*/case.json'))


def test_classifier_routes():
    assert classify('Turn my portrait into a Roman bronze bust', True)=='artifact_transform'
    assert classify('Make me a Tang court woman at a lantern festival', False)=='historical_portrait'
    assert classify('Turn this reference into watercolor', True)=='reference_transform'
    assert classify('Create a 16-panel storyboard', False)=='storyboard_or_grid'


def test_all_golden_cases_lint_and_compile():
    assert len(golden())==10
    for p in golden():
        spec=json.loads(p.read_text(encoding='utf-8'))
        errors=[f for f in lint_spec(spec) if f['level']=='error']
        assert not errors, (p,errors)
        prompt=compile_prompt(spec)
        assert len(prompt)>300
        assert 'Reference discipline:' in prompt or not spec['references']


def test_wuxia_cannot_be_only_era():
    spec=json.loads(golden()[0].read_text(encoding='utf-8'))
    spec['historical']['packs']=['wuxia']
    spec['historical']['region']=None
    findings=lint_spec(spec)
    assert any(x['code']=='genre_as_era' and x['level']=='error' for x in findings)


def test_dunhuang_strict_requires_narrowing():
    spec=json.loads(golden()[4].read_text(encoding='utf-8'))
    spec['historical']['strictness']='strict_reconstruction'
    spec['historical']['subperiod']=None
    findings=lint_spec(spec)
    assert any(x['code']=='dunhuang_strict_narrowing' for x in findings)


def test_reference_roles_are_isolated_in_prompt():
    spec=json.loads((ROOT/'cases/golden/08-edo-blue-white-ceramic/case.json').read_text(encoding='utf-8'))
    prompt=compile_prompt(spec)
    assert 'supplies identity only' in prompt
    assert 'Do not import unassigned identity, body, clothing, objects, layout, or style' in prompt


def test_art_methods_have_required_behavior():
    registry=load('references/art-methods/registry.json')
    assert len(registry['methods'])==12
    for row in registry['methods']:
        m=load(row['path'])
        for key in ['material','fabrication_process','visible_production_marks','edge_behavior','color_behavior','surface_behavior','composition_behavior','structural_limitations','aging_weathering','artifact_compatibility','typical_generation_failures','evaluation_criteria']:
            assert m.get(key), (m['id'],key)


def test_era_packs_and_overlay_types():
    registry=load('references/eras/registry.json')
    assert len(registry['packs'])==13
    packs={r['id']:load(r['path']) for r in registry['packs']}
    assert packs['wuxia']['pack_type']=='genre_overlay'
    assert packs['xianxia']['pack_type']=='fantasy_overlay'
    assert packs['dunhuang']['pack_type']=='site_tradition'
    assert packs['ming']['pack_type']=='historical_era'


def test_surgical_revision_preserves_success():
    ev=load('evaluation/example_evaluation.json')
    txt=surgical_revision(ev)
    assert 'Preserve exactly what already works' in txt
    assert 'material_failure' in txt
    assert 'Do not introduce new wardrobe' in txt


def test_prompt_linter_flags_keyword_stack():
    findings=lint_prompt('masterpiece best quality 8K ultra HD portrait')
    assert any(x['code']=='quality_keyword_stack' for x in findings)
