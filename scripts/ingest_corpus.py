#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from aipf.corpus import ingest
ap=argparse.ArgumentParser(); ap.add_argument('source'); ap.add_argument('--output-dir',default=str(ROOT/'corpus/indexes')); a=ap.parse_args()
print(json.dumps(ingest(a.source,a.output_dir),ensure_ascii=False,indent=2))
