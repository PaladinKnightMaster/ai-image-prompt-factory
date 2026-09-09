from __future__ import annotations
import argparse,json
from pathlib import Path
from .classifier import classify
from .compiler import compile_prompt,compile_result
from .linting import lint_spec,lint_prompt
from .evidence import evidence_explain
from .compatibility import audit_compatibility
from .diffing import semantic_diff,prompt_semantic_diff
from .corpus import ingest
from .config import corpus_path
from .regression import run_regression,build_baselines,compare_baselines
from .evaluation import evaluation_template,surgical_revision,surgical_revision_plan
from .patterns import all_patterns,get_pattern
from .experiments import load_experiment,plan_experiment,experiment_inventory,experiment_report
from .benchmarks import benchmark_report
from .prompt_mechanisms import quality_audit
from .experiment_runs import create_run_plan, write_run_plan


def _load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def _dump(x): print(json.dumps(x,ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser(prog='aipf'); sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('classify'); p.add_argument('request'); p.add_argument('--has-reference',action='store_true')
    p=sub.add_parser('compile'); p.add_argument('spec'); p.add_argument('--profile',choices=['compact','standard','extended']); p.add_argument('--json',action='store_true',dest='as_json')
    p=sub.add_parser('audit'); p.add_argument('spec')
    p=sub.add_parser('evidence'); p.add_argument('spec')
    p=sub.add_parser('lint'); p.add_argument('input'); p.add_argument('--prompt',action='store_true')
    p=sub.add_parser('diff'); p.add_argument('old'); p.add_argument('new'); p.add_argument('--prompt',action='store_true')
    p=sub.add_parser('regress'); p.add_argument('case_root',nargs='?'); p.add_argument('--output')
    p=sub.add_parser('baseline'); p.add_argument('case_root',nargs='?'); p.add_argument('--output')
    p=sub.add_parser('baseline-check'); p.add_argument('baseline'); p.add_argument('case_root',nargs='?'); p.add_argument('--output')
    p=sub.add_parser('ingest'); p.add_argument('source', nargs='?', help='Corpus root. Defaults to AIPF_CORPUS_PATH.'); p.add_argument('--output-dir',default='corpus/indexes')
    p=sub.add_parser('evaluation-template'); p.add_argument('spec'); p.add_argument('--output')
    p=sub.add_parser('revision'); p.add_argument('evaluation'); p.add_argument('--json',action='store_true',dest='as_json')
    p=sub.add_parser('patterns'); p.add_argument('pattern_id',nargs='?')
    p=sub.add_parser('experiment-plan'); p.add_argument('experiment')
    p=sub.add_parser('experiment-inventory')
    p=sub.add_parser('benchmark-report')
    p=sub.add_parser('prompt-audit'); p.add_argument('prompt')
    p = sub.add_parser("experiment-run-plan"); p.add_argument("experiment"); p.add_argument("--replicates", type=int, default=4); p.add_argument("--size", default="1024x1536"); p.add_argument("--quality", default="medium"); p.add_argument("--output");

    args=ap.parse_args()
    if args.cmd=='classify': print(classify(args.request,args.has_reference)); return
    if args.cmd=='compile':
        r=compile_result(_load(args.spec),args.profile); _dump(r) if args.as_json else print(r['prompt'],end=''); return
    if args.cmd=='audit':
        spec=_load(args.spec); _dump(compile_result(spec)['compatibility_audit']); return
    if args.cmd=='evidence': _dump(evidence_explain(_load(args.spec))); return
    if args.cmd=='lint':
        obj=Path(args.input).read_text(encoding='utf-8') if args.prompt else _load(args.input); _dump(lint_prompt(obj) if args.prompt else lint_spec(obj)); return
    if args.cmd=='diff':
        if args.prompt: _dump(prompt_semantic_diff(Path(args.old).read_text(encoding='utf-8'),Path(args.new).read_text(encoding='utf-8')))
        else: _dump(semantic_diff(_load(args.old),_load(args.new))); return
    if args.cmd=='regress':
        r=run_regression(args.case_root); _dump(r); 
        if args.output:
            op=Path(args.output); op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise SystemExit(0 if r['ok'] else 1)
    if args.cmd=='baseline':
        r=build_baselines(args.case_root); _dump(r)
        if args.output:
            op=Path(args.output); op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return
    if args.cmd=='baseline-check':
        r=compare_baselines(args.baseline,args.case_root); _dump(r)
        if args.output:
            op=Path(args.output); op.parent.mkdir(parents=True,exist_ok=True); op.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise SystemExit(0 if r['ok'] else 1)
    if args.cmd == 'ingest':
        source = Path(args.source).expanduser().resolve() if args.source else corpus_path()

        if source is None:
            ap.error(
                'ingest requires a source path or AIPF_CORPUS_PATH '
                'configured in .env/environment'
            )

        if not source.exists():
            ap.error(f'corpus path does not exist: {source}')

        _dump(ingest(source, args.output_dir))
        return
    if args.cmd=='evaluation-template':
        spec=_load(args.spec); ev=evaluation_template(spec.get('id',Path(args.spec).stem),spec); _dump(ev)
        if args.output: Path(args.output).write_text(json.dumps(ev,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return
    if args.cmd=='revision':
        ev=_load(args.evaluation); _dump(surgical_revision_plan(ev)) if args.as_json else print(surgical_revision(ev),end=''); return
    if args.cmd=='patterns': _dump(get_pattern(args.pattern_id) if args.pattern_id else {'patterns':all_patterns()}); return
    if args.cmd=='experiment-plan': _dump(plan_experiment(load_experiment(args.experiment))); return
    if args.cmd=='experiment-inventory': _dump(experiment_inventory()); return
    if args.cmd=='benchmark-report': _dump(benchmark_report()); return
    if args.cmd=='prompt-audit': _dump(quality_audit(Path(args.prompt).read_text(encoding='utf-8'))); return
    if args.cmd == "experiment-run-plan":
        run = create_run_plan(
            args.experiment,
            replicates=args.replicates,
            size=args.size,
            quality=args.quality,
        )

        path = write_run_plan(
            run,
            args.output,
        )

        _dump(
            {
                "run_id": run["run_id"],
                "experiment_id": run["experiment_id"],
                "variants": len(run["variants"]),
                "replicates": args.replicates,
                "run_file": str(path),
            }
        )
        return

if __name__=='__main__': main()
