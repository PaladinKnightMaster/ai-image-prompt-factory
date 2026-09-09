from __future__ import annotations
from collections import Counter,defaultdict
from hashlib import sha256
from pathlib import Path,PurePosixPath
from zipfile import ZipFile
import json,re,os
from .prompt_mechanisms import decompose_prompt

IMAGE_EXTS={'.jpg','.jpeg','.png','.webp'}
COLLECTIONS={
 'APC':{'collection_name':'AIPixLab Collection','source_document':'Image-Kit/AIPixLab Collection.md','source_platform':'X','creator':'AIPixLab','provenance_status':'verified_by_project_owner'},
 'FSC':{'collection_name':'Fashion Style Collections','source_document':'Image-Kit/Fashion Style Collections.md','source_platform':'X','creator':None,'provenance_status':'verified_by_project_owner'},
 'GAC':{'collection_name':'Game_Anim Style Collections','source_document':'Image-Kit/Game_Anim Style Collections.md','source_platform':'X','creator':None,'provenance_status':'verified_by_project_owner'},
 'LCC':{'collection_name':'Larus Canus Collection','source_document':'Image-Kit/Larus Canus Collection.md','source_platform':'X','creator':'MrLarus','creator_url':'https://x.com/MrLarus','provenance_status':'verified_by_project_owner'},
 'LAC':{'collection_name':'Liyue AI Collection','source_document':'Image-Kit/Liyue AI Collection.md','source_platform':'X','creator':'Liyue AI','creator_url':'https://x.com/liyue_ai','provenance_status':'verified_by_project_owner'},
}


def _jpeg_dimensions(fp):
    try:
        if fp.read(2)!=b'\xff\xd8': return None
        while True:
            b=fp.read(1)
            if not b: return None
            if b!=b'\xff': continue
            while b==b'\xff': b=fp.read(1)
            marker=b[0]
            if marker in {0xD8,0xD9}: continue
            ln=fp.read(2)
            if len(ln)<2: return None
            n=int.from_bytes(ln,'big')
            if n<2: return None
            if marker in {0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF}:
                data=fp.read(n-2)
                if len(data)>=5: return {'width':int.from_bytes(data[3:5],'big'),'height':int.from_bytes(data[1:3],'big')}
                return None
            fp.seek(n-2,1)
    except Exception: return None


def _hash_stream(fp,chunk=1024*1024):
    h=sha256()
    while True:
        b=fp.read(chunk)
        if not b: break
        h.update(b)
    return h.hexdigest()


def _collection_from_path(path:str)->str:
    p=PurePosixPath(path); parts=p.parts
    if 'SAMPLE_OUTPUT' in parts:
        i=parts.index('SAMPLE_OUTPUT')
        if len(parts)>i+1: return parts[i+1]
    return p.parent.name or 'root'


def _sample_group(path:str)->str|None:
    stem=PurePosixPath(path).stem
    m=re.match(r'([A-Z]{3})_(\d{4})',stem)
    return f'{m.group(1)}_{m.group(2)}' if m else None


def _tags_from_path(path:str)->list[str]:
    s=path.casefold(); tags=[]
    mapping={'wuxia':'wuxia','greek':'classical_greek','roman':'roman','watercolor':'watercolor','paper':'paper_craft','museum':'museum','historical':'historical','fashion':'fashion','gravure':'portrait_pose','hairstyle':'hair','product':'product','brand':'brand','marketing':'marketing'}
    for needle,tag in mapping.items():
        if needle in s: tags.append(tag)
    return tags


def _collection_meta(code:str)->dict:
    return COLLECTIONS.get(code,{'collection_name':code,'source_document':None,'source_platform':None,'creator':None,'provenance_status':'unknown'})


def _asset_record(path:str,size:int,digest:str,dimensions,source_name:str)->dict:
    code=_collection_from_path(path); meta=_collection_meta(code); ext=PurePosixPath(path).suffix.lower().lstrip('.')
    return {
      'asset_id':'asset-'+digest[:20], 'sha256':digest,'relative_path':path,'bytes':size,'format':ext,'dimensions':dimensions,
      'source_collection':code,'collection_name':meta.get('collection_name'),'sample_group':_sample_group(path),
      'associated_prompt_id':None,'associated_prompt':None,'prompt_association_confidence':'unknown','source_url':None,
      'creator':meta.get('creator'),'creator_url':meta.get('creator_url'),'source_platform':meta.get('source_platform'),
      'source_document':meta.get('source_document'),'provenance_status':meta.get('provenance_status'),
      'license_status':'private_reference' if code in COLLECTIONS else 'unknown_license','redistribution_status':'private_only' if code in COLLECTIONS else 'metadata_only','tags':_tags_from_path(path),'promotion_status':'unreviewed',
      'source_archive':source_name
    }


def _scan_zip(path:Path)->tuple[list[dict],list[dict],dict[str,str]]:
    assets=[]; docs=[]; texts={}
    with ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir(): continue
            ext=PurePosixPath(info.filename).suffix.lower()
            if ext in IMAGE_EXTS:
                with z.open(info) as fp: digest=_hash_stream(fp)
                dimensions=None
                if ext in {'.jpg','.jpeg'}:
                    with z.open(info) as fp: dimensions=_jpeg_dimensions(fp)
                assets.append(_asset_record(info.filename,info.file_size,digest,dimensions,path.name))
            elif ext in {'.md','.txt','.json'}:
                with z.open(info) as fp: raw=fp.read()
                digest=sha256(raw).hexdigest(); texts[info.filename]=raw.decode('utf-8',errors='replace')
                docs.append({'relative_path':info.filename,'bytes':info.file_size,'format':ext.lstrip('.'),'sha256':digest,'source_archive':path.name,'redistribution_status':'internal_only','license_status':'internal_approved_unspecified_license'})
    return assets,docs,texts


def _scan_dir(path:Path)->tuple[list[dict],list[dict],dict[str,str]]:
    assets=[]; docs=[]; texts={}
    for p in sorted(x for x in path.rglob('*') if x.is_file()):
        rel=p.relative_to(path).as_posix(); ext=p.suffix.lower(); raw=p.read_bytes(); digest=sha256(raw).hexdigest()
        if ext in IMAGE_EXTS:
            dimensions=None
            if ext in {'.jpg','.jpeg'}:
                with p.open('rb') as fp: dimensions=_jpeg_dimensions(fp)
            assets.append(_asset_record(rel,p.stat().st_size,digest,dimensions,path.name))
        elif ext in {'.md','.txt','.json'}:
            texts[rel]=raw.decode('utf-8',errors='replace')
            docs.append({'relative_path':rel,'bytes':p.stat().st_size,'format':ext.lstrip('.'),'sha256':digest,'source_archive':path.name,'redistribution_status':'internal_only','license_status':'internal_approved_unspecified_license'})
    return assets,docs,texts


def _sections(markdown:str)->list[tuple[str,str]]:
    # Split headings only outside fenced blocks.
    lines=markdown.replace('\r\n','\n').splitlines(); sections=[]; current_title='Introduction'; buf=[]; fenced=False
    for line in lines:
        if line.strip().startswith('```'):
            fenced=not fenced; buf.append(line); continue
        if not fenced and re.match(r'^#{1,3}\s+',line):
            if buf: sections.append((current_title,'\n'.join(buf).strip()))
            current_title=re.sub(r'^#{1,3}\s+','',line).strip() or 'Untitled'; buf=[]
        else: buf.append(line)
    if buf: sections.append((current_title,'\n'.join(buf).strip()))
    return sections


def _extract_prompt_candidates(section:str)->list[str]:
    out=[]
    fences=re.findall(r'```(?:text|json|markdown)?\s*\n(.*?)```',section,flags=re.S|re.I)
    for x in fences:
        s=x.strip()
        if len(s)>=120 and not s.startswith('{"schema_version"'): out.append(s)
    # Unfenced Prompt: blocks until blank + metadata line or marker.
    for m in re.finditer(r'(?im)^\s*(?:prompt(?: template)?|completed prompt|finished look prompt)\s*:\s*$',section):
        rest=section[m.end():]
        chunk=re.split(r'(?im)^\s*(?:\*\s*SAMPLE OUTPUT|#{1,3}\s+|={5,})',rest,maxsplit=1)[0].strip()
        chunk=re.sub(r'^```(?:text|json)?\s*|```$','',chunk,flags=re.I|re.S).strip()
        if len(chunk)>=120: out.append(chunk)
    # preserve order / dedup
    seen=set(); result=[]
    for x in out:
        key=sha256(x.encode()).hexdigest()
        if key not in seen: seen.add(key); result.append(x)
    return result


def _sample_groups_in_section(section:str)->list[str]:
    groups=[]
    for m in re.finditer(r'SAMPLE OUTPUT\s*-\s*([A-Z]{3}_\d{4})',section,flags=re.I): groups.append(m.group(1).upper())
    return list(dict.fromkeys(groups))


def build_prompt_index(texts:dict[str,str])->dict:
    records=[]
    for code,meta in COLLECTIONS.items():
        doc=meta['source_document']; text=texts.get(doc)
        if not text: continue
        n=0
        for title,section in _sections(text):
            prompts=_extract_prompt_candidates(section); groups=_sample_groups_in_section(section)
            for prompt in prompts:
                n+=1; digest=sha256(prompt.encode()).hexdigest()
                records.append({
                  'prompt_id':f'{code}-P{n:04d}','sha256':digest,'source_collection':code,'collection_name':meta['collection_name'],
                  'creator':meta.get('creator'),'creator_url':meta.get('creator_url'),'source_platform':meta.get('source_platform'),
                  'source_document':doc,'section_title':title,'sample_groups':groups,'prompt_text':prompt,
                  'decomposition':decompose_prompt(prompt),'provenance_status':meta['provenance_status'],'scope':'internal_source'
                })
    return {'schema_version':'1.0','prompt_records':records}


def associate_assets(assets:list[dict],prompt_index:dict)->dict:
    group_map=defaultdict(list)
    for p in prompt_index['prompt_records']:
        for g in p.get('sample_groups',[]): group_map[g].append(p)
    exact=probable=0
    for a in assets:
        g=a.get('sample_group'); candidates=group_map.get(g,[])
        if len(candidates)==1:
            p=candidates[0]; a['associated_prompt_id']=p['prompt_id']; a['associated_prompt']=p['prompt_text']; a['prompt_association_confidence']='exact_section'; exact+=1
        elif len(candidates)>1:
            # Ambiguous section: preserve uncertainty rather than attaching an arbitrary prompt.
            pass
    return {'exact_section':exact,'probable_section':probable,'unknown':len(assets)-exact-probable}


def _pattern_observations(prompt_index:dict)->dict:
    rules={
      'pose-explicit-weight-distribution':['weight shifted','weight on one leg','body weight','center of gravity'],
      'pose-one-knee-active-sit':['one knee raised','one-knee','one knee up'],
      'pose-shallow-chair-sit':['sitting shallowly','seated shallowly'],
      'pose-over-shoulder-turn':['over the shoulder','looking back'],
      'pose-forward-lean-support':['leaning forward','forward-leaning'],
      'interaction-hand-hair':['touching her hair','touching hair','hand near her hair'],
      'composition-layered-depth':['foreground','midground','background','前景','中景','背景'],
      'composition-negative-space':['negative space','留白'],
      'composition-asymmetric-editorial':['asymmetry','asymmetrical'],
      'lighting-window-side':['window light','side light'],
      'lighting-soft-directional':['soft directional','directional side light'],
      'material-satin-fold-response':['satin','fabric folds'],
      'material-bronze-cast-patina':['bronze','patina'],
      'material-marble-carving-weathering':['marble','carved'],
      'material-watercolor-edge-behavior':['watercolor','paper texture'],
      'material-porcelain-glaze-underglaze':['porcelain','glaze'],
      'narrative-micro-action':['as if','caught in','moment'],
      'interaction-explicit-prop':['holding','touching','resting on'],
      'story-environmental-detail':['environmental storytelling','background features','scene:'],
      'prompt-structure-then-emotion':['composition:','mood','构图','氛围'],
      'prompt-targeted-constraints':['avoid:','avoid ','避免','不要','禁止'],
      'prompt-medium-anchor':['film photography','watercolor','woodblock','porcelain','bronze','marble'],
      'reference-role-explicit':['reference image','identity preservation','use uploaded','参考图','身份保持'],
    }
    obs={k:[] for k in rules}
    for p in prompt_index['prompt_records']:
        low=p['prompt_text'].casefold()
        for pid,terms in rules.items():
            if any(t in low for t in terms):
                obs[pid].append(p['prompt_id'])
    return {k:v[:12] for k,v in obs.items() if v}


def ingest(source:str|Path,output_dir:str|Path)->dict:
    source=Path(source); output_dir=Path(output_dir); output_dir.mkdir(parents=True,exist_ok=True)
    source_digest=None
    if source.is_file():
        with source.open('rb') as fp: source_digest=_hash_stream(fp)
    if source.suffix.lower()=='.zip': assets,docs,texts=_scan_zip(source)
    elif source.is_dir(): assets,docs,texts=_scan_dir(source)
    else: raise ValueError(f'Unsupported corpus source: {source}')
    prompts=build_prompt_index(texts); assoc=associate_assets(assets,prompts)
    by_hash=defaultdict(list)
    for a in assets: by_hash[a['sha256']].append(a['relative_path'])
    duplicate_groups=[{'sha256':h,'paths':paths,'count':len(paths)} for h,paths in by_hash.items() if len(paths)>1]
    collections=Counter(a['source_collection'] for a in assets)
    manifest={'schema_version':'2.0','scope':'internal_dev','source_name':source.name,'source_sha256':source_digest,'collection_metadata':COLLECTIONS,'assets':assets,'documents':docs}
    observations=_pattern_observations(prompts)
    report={
      'source_name':source.name,'source_sha256':source_digest,'image_assets':len(assets),'text_documents':len(docs),'unique_hashes':len(by_hash),
      'exact_duplicate_groups':len(duplicate_groups),'exact_duplicate_extra_files':sum(x['count']-1 for x in duplicate_groups),
      'collections':dict(sorted(collections.items())),'prompt_records':len(prompts['prompt_records']),'image_prompt_associations':assoc,
      'verified_provenance_assets':sum(a.get('provenance_status')=='verified_by_project_owner' for a in assets),
      'internal_only_assets':sum(a.get('redistribution_status')=='private_only' for a in assets),'public_gallery_eligible':0,
      'pattern_observation_types':len(observations),
      'policy':'Collected source assets are internal development material. Public release packaging excludes the raw source corpus and internal gallery output.'
    }
    (output_dir/'image_library_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output_dir/'prompt_index.json').write_text(json.dumps(prompts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output_dir/'duplicate_index.json').write_text(json.dumps({'groups':duplicate_groups},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output_dir/'ingestion_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output_dir/'pattern_observations.json').write_text(json.dumps({'schema_version':'1.0','observations':observations},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


def corpus_path_from_env()->Path|None:
    value=os.environ.get('AIPF_CORPUS_PATH')
    return Path(value).expanduser().resolve() if value else None
