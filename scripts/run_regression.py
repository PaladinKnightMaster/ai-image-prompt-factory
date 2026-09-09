#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from aipf.regression import run_regression
r=run_regression()
out=ROOT/'regression/reports/latest.json'; out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:r[k] for k in ['ok','cases','passed','failed']},indent=2))
raise SystemExit(0 if r['ok'] else 1)
