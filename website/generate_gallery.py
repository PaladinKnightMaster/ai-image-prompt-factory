#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json,html

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'website/generated'
GROUPS=['golden','public','experimental','regression']
PUBLIC_STATUSES={'publishable','first_party','generated_by_project'}


def _read(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def _output_public(case,p):
    rec=case.get('case_record',{}); image=rec.get('output_image')
    if not image: return None
    status=rec.get('output_publication_status') or rec.get('redistribution_status')
    # V3.2 fails closed: legacy/unknown status is not public.
    if status not in PUBLIC_STATUSES: return None
    target=p.parent/image
    return str(target.relative_to(ROOT)) if target.exists() else None


def records():
    out=[]
    for group in GROUPS:
        for p in sorted((ROOT/'cases'/group).glob('*/case.json')):
            case=_read(p); rec=case.get('case_record',{})
            prompt_path=p.parent/(rec.get('compiled_prompt') or 'compiled_prompt.md')
            snap_path=p.parent/(rec.get('evidence_snapshot') or 'evidence_snapshot.json')
            audit_path=p.parent/(rec.get('compatibility_audit') or 'compatibility_audit.json')
            ev_path=p.parent/(rec.get('evaluation') or 'evaluation.json') if rec.get('evaluation') else None
            snapshot=_read(snap_path) if snap_path.exists() else None
            audit=_read(audit_path) if audit_path.exists() else None
            evaluation=_read(ev_path) if ev_path and ev_path.exists() else None
            claims=[x['claim_id'] for x in (snapshot or {}).get('claims',[])]
            sources=[x.get('institution') or x.get('title') for x in (snapshot or {}).get('sources',[])]
            out.append({
              'group':group,'id':case.get('id'),'title':case.get('title',case.get('id')),'status':case.get('status','unknown'),
              'request':case.get('request'),'route':case.get('route'),'historical':case.get('historical',{}),'art':case.get('art',{}),
              'profile':case.get('output',{}).get('profile'),'aspect_ratio':case.get('output',{}).get('aspect_ratio'),'references':case.get('references',[]),
              'compiled_prompt':prompt_path.read_text(encoding='utf-8') if prompt_path.exists() else None,
              'evidence':{'claim_ids':claims,'source_labels':list(dict.fromkeys(x for x in sources if x)),'snapshot_sha256':(snapshot or {}).get('snapshot_sha256')},
              'compatibility_summary':(audit or {}).get('summary'), 'evaluation_scores':(evaluation or {}).get('scores'),
              'revision_count':len(rec.get('revision_history',[])),
              'model':{'alias':rec.get('model_version'),'snapshot':rec.get('model_snapshot'),'compiler':rec.get('compiler_version'),'skill':rec.get('skill_version')},
              'output_image':_output_public(case,p),'relative_case':str(p.relative_to(ROOT))
            })
    return out


def make_html(data):
    cards=[]
    for c in data:
        packs=', '.join(c['historical'].get('packs',[])) or 'none'; method=c['art'].get('method') or 'living / non-artifact'; form=c['art'].get('artifact_form') or '—'
        strict=c['historical'].get('strictness') or '—'; prompt=(c['compiled_prompt'] or 'Not compiled yet').replace('# Compiled Prompt','').strip()
        claims=', '.join(c['evidence']['claim_ids']) or 'none selected'; sources=', '.join(c['evidence']['source_labels']) or 'none selected'
        cs=c['compatibility_summary'] or {}; score=c['evaluation_scores'] or {}
        image=f'<img src="../../{html.escape(c["output_image"])}" alt="{html.escape(c["title"])}">' if c['output_image'] else '<div class="noimg">No publishable output image attached</div>'
        cards.append(f'''<article class="case" data-group="{html.escape(c['group'])}" data-era="{html.escape(' '.join(c['historical'].get('packs',[])))}" data-method="{html.escape(method)}">
  <div class="eyebrow">{html.escape(c['group'])} · {html.escape(c['route'])}</div>
  <h2>{html.escape(c['title'])}</h2>
  {image}
  <p class="request">“{html.escape(c['request'])}”</p>
  <div class="chips"><span>{html.escape(packs)}</span><span>{html.escape(strict)}</span><span>{html.escape(method)}</span><span>{html.escape(form)}</span><span>{html.escape(c['aspect_ratio'] or '')}</span></div>
  <details><summary>Compiled prompt</summary><pre>{html.escape(prompt)}</pre></details>
  <details><summary>Evidence & audit</summary><p><b>Claims:</b> {html.escape(claims)}</p><p><b>Sources:</b> {html.escape(sources)}</p><p><b>Compatibility:</b> {html.escape(json.dumps(cs,ensure_ascii=False))}</p></details>
  <div class="audit">Model: {html.escape(str(c['model'].get('snapshot') or c['model'].get('alias') or 'not generated'))} · Evaluation: {html.escape(json.dumps(score,ensure_ascii=False) if score else 'not run')} · Revisions: {c['revision_count']}<br>Spec: <code>{html.escape(c['relative_case'])}</code></div>
</article>''')
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Image Prompt Factory V3.2 Gallery</title><style>
:root{{--bg:#f6f4ef;--ink:#1f2328;--muted:#656d76;--card:#fff;--line:#d8d2c8;--accent:#5b4b3a}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}}header,main{{max-width:1180px;margin:auto;padding:32px 24px}}header{{padding-top:56px}}h1{{font-size:clamp(38px,6vw,70px);letter-spacing:-.04em;line-height:1;margin:.15em 0}}header p{{max-width:820px;color:var(--muted);font-size:18px}}.filters{{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}}select{{padding:8px 12px;border:1px solid var(--line);border-radius:10px;background:white}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:18px}}.case{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;box-shadow:0 7px 24px rgba(0,0,0,.04)}}.case img{{width:100%;border-radius:12px}}.noimg{{border:1px dashed var(--line);border-radius:12px;padding:18px;color:var(--muted);font-size:13px}}.eyebrow{{text-transform:uppercase;letter-spacing:.08em;font-size:12px;color:var(--muted)}}h2{{font-size:23px;line-height:1.2}}.request{{min-height:64px}}.chips{{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0}}.chips span{{border:1px solid var(--line);border-radius:999px;padding:4px 9px;font-size:12px;color:var(--accent)}}details{{margin-top:14px}}summary{{cursor:pointer;font-weight:650}}pre{{white-space:pre-wrap;font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;background:#f4f2ed;padding:14px;border-radius:10px;max-height:420px;overflow:auto}}.audit{{margin-top:14px;color:var(--muted);font-size:12px}}code{{font-size:11px}}</style></head><body>
<header><div class="eyebrow">Evidence-backed case gallery</div><h1>AI Image Prompt Factory V3.2</h1><p>Generated from the same case records, evidence snapshots, compatibility audits and model metadata used by the compiler/regression suite. Internal source-corpus images are never published by this page.</p><div class="filters"><select id="group"><option value="">All groups</option>{''.join(f'<option>{g}</option>' for g in GROUPS)}</select><select id="era"><option value="">All eras/overlays</option>{''.join(f'<option>{html.escape(x)}</option>' for x in sorted({p for c in data for p in c['historical'].get('packs',[])}))}</select><select id="method"><option value="">All art methods</option>{''.join(f'<option>{html.escape(x)}</option>' for x in sorted({c['art'].get('method') for c in data if c['art'].get('method')}))}</select></div></header>
<main class="grid">{''.join(cards)}</main><script>const byId=id=>document.getElementById(id);for(const id of ['group','era','method'])byId(id).addEventListener('change',()=>{{const g=byId('group').value,e=byId('era').value,m=byId('method').value;for(const c of document.querySelectorAll('.case'))c.style.display=(!g||c.dataset.group===g)&&(!e||c.dataset.era.split(' ').includes(e))&&(!m||c.dataset.method===m)?'block':'none'}});</script></body></html>'''


def main():
    OUT.mkdir(parents=True,exist_ok=True); data=records()
    (OUT/'cases.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'index.html').write_text(make_html(data),encoding='utf-8')
    print(json.dumps({'cases':len(data),'publishable_images':sum(bool(x['output_image']) for x in data),'json':str((OUT/'cases.json').relative_to(ROOT)),'html':str((OUT/'index.html').relative_to(ROOT))},indent=2))

if __name__=='__main__': main()
