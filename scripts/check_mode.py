#!/usr/bin/env python3
import argparse, json, os

def truthy(v): return str(v or '').strip().lower() in {'1','true','yes','on'}

def detect():
    direct=truthy(os.getenv('AIPF_DIRECT_API'))
    key=bool(os.getenv('OPENAI_API_KEY'))
    host=truthy(os.getenv('AIPF_HOST_NATIVE'))
    if direct and key:
        return {'mode':'DIRECT_API','can_execute':True,'recommendation':'Compile the prompt first; execute direct API only if the user requested generation/editing.'}
    if direct and not key:
        return {'mode':'DIRECT_API?','can_execute':False,'recommendation':'Direct API requested but OPENAI_API_KEY is missing; remain prompt-only or use host-native tooling.'}
    if host:
        return {'mode':'HOST_NATIVE','can_execute':True,'recommendation':'Compile the prompt, then delegate to the host image tool only if generation/editing was requested.'}
    return {'mode':'ADVISOR','can_execute':False,'recommendation':'Return/save the compiled prompt; do not claim an image was generated.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); d=detect()
    print(json.dumps(d,indent=2) if a.json else f"{d['mode']}: {d['recommendation']}")
