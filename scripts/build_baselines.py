#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from aipf.regression import build_baselines
b=build_baselines(); out=ROOT/'regression/baselines/golden_baselines.json'; out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'golden_baselines':len(b['baselines']),'path':str(out.relative_to(ROOT))},indent=2))
