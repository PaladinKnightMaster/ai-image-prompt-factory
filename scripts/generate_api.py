#!/usr/bin/env python3
"""Explicit GPT Image 2 API executor with reproducibility metadata.

Compilation is separate from execution. Without --execute this script performs a dry run.
No unsupported seed or hidden parameter is invented.
"""
from __future__ import annotations
import argparse,base64,json,os,hashlib
from datetime import datetime,timezone
from pathlib import Path


def read_prompt(args):
    if args.prompt_file: return Path(args.prompt_file).read_text(encoding='utf-8').strip()
    if args.prompt: return args.prompt.strip()
    raise SystemExit('Provide --prompt or --prompt-file')


def sha256_file(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def save_result(result,output:Path):
    datum=result.data[0]; b64=getattr(datum,'b64_json',None)
    if b64:
        output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(base64.b64decode(b64))
        return {'saved':str(output),'transport':'b64_json','output_sha256':sha256_file(output)}
    url=getattr(datum,'url',None)
    if url: return {'url':url,'transport':'url','note':'Remote URL returned; download explicitly if desired.'}
    return {'note':'API returned no recognized b64_json/url field.'}


def write_metadata(args,prompt,mode,result_meta=None,dry_run=False):
    refs=[]
    for p in args.image or []:
        path=Path(p); refs.append({'path':str(path),'sha256':sha256_file(path) if path.exists() else None})
    metadata={
      'schema_version':'3.1','provider':'openai','model':args.model,'model_snapshot':args.model_snapshot,
      'generation_date_utc':datetime.now(timezone.utc).isoformat(),'mode':mode,'prompt_profile':args.prompt_profile,
      'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'input_references':refs,'size':args.size,'quality':args.quality,
      'background':args.background,'compiler_version':args.compiler_version,'skill_version':'3.2.0','seed':None,
      'dry_run':dry_run,'result':result_meta or {}
    }
    if args.metadata_output:
        p=Path(args.metadata_output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return metadata


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prompt'); ap.add_argument('--prompt-file')
    ap.add_argument('--image',action='append',help='Reference image path; one or more switches API call to edit mode')
    ap.add_argument('--model',default=os.getenv('OPENAI_IMAGE_MODEL','gpt-image-2'))
    ap.add_argument('--model-snapshot',default=os.getenv('OPENAI_IMAGE_MODEL_SNAPSHOT','gpt-image-2-2026-04-21'))
    ap.add_argument('--size',default='auto'); ap.add_argument('--quality',choices=['low','medium','high','auto'],default='auto')
    ap.add_argument('--background',choices=['transparent','opaque','auto']); ap.add_argument('--output',default='aipf-output.png')
    ap.add_argument('--prompt-profile',choices=['compact','standard','extended'],default='standard'); ap.add_argument('--compiler-version',default='3.2.0')
    ap.add_argument('--metadata-output',help='Write generation/dry-run metadata JSON')
    ap.add_argument('--execute',action='store_true',help='Actually call the API. Omit for dry-run payload inspection.')
    args=ap.parse_args(); prompt=read_prompt(args); mode='edit' if args.image else 'generate'
    payload={'mode':mode,'model':args.model,'model_snapshot':args.model_snapshot,'prompt':prompt,'size':args.size,'quality':args.quality}
    if args.background: payload['background']=args.background
    if args.image: payload['images']=args.image
    if not args.execute:
        metadata=write_metadata(args,prompt,mode,dry_run=True)
        print(json.dumps({'dry_run':True,**payload,'metadata':metadata},ensure_ascii=False,indent=2)); return
    if not os.getenv('OPENAI_API_KEY'): raise SystemExit('OPENAI_API_KEY is required with --execute')
    try: from openai import OpenAI
    except ImportError as e: raise SystemExit('Install API support with: pip install -e .[api]') from e
    client=OpenAI(); kwargs={'model':args.model,'prompt':prompt}
    if args.size!='auto': kwargs['size']=args.size
    if args.quality!='auto': kwargs['quality']=args.quality
    if args.background and args.background!='auto': kwargs['background']=args.background
    if args.image:
        handles=[open(p,'rb') for p in args.image]
        try:
            kwargs['image']=handles if len(handles)>1 else handles[0]; result=client.images.edit(**kwargs)
        finally:
            for h in handles: h.close()
    else: result=client.images.generate(**kwargs)
    result_meta=save_result(result,Path(args.output)); metadata=write_metadata(args,prompt,mode,result_meta=result_meta,dry_run=False)
    print(json.dumps({'result':result_meta,'metadata':metadata},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
