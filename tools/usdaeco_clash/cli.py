"""Run mesh or exact clash tests and compare their measured results."""
import argparse
import json
import os
from pathlib import Path
import sys
from pxr import Plug, Usd
from .comparison import compare


def register():
    root = Path(__file__).resolve().parents[2]
    core = Path(os.environ.get('CORE_PLUGIN_DIR',root.parent/'usdaeco-core/out/plugins/usdAeco/resources'))
    Plug.Registry().RegisterPlugins(str(core))
    Plug.Registry().RegisterPlugins(str(root/'usdAecoClash'))
    if not Usd.SchemaRegistry().FindConcretePrimDefinition('AecoClashTest'):
        raise RuntimeError('Clash schema is unavailable; build the resource plugin first')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    run = sub.add_parser('run')
    run.add_argument('stage',type=Path)
    run.add_argument('--test',required=True)
    run.add_argument('--output',type=Path,required=True)
    run.add_argument('--json',type=Path)
    run.add_argument('--method',choices=('mesh','exact'),help='Override the test method without editing its drivers')
    cmp = sub.add_parser('compare')
    cmp.add_argument('findings',type=Path,help='JSON result list produced by run --json')
    cmp.add_argument('--exact',type=Path,help='Exact JSON result list produced by run --method exact --json')
    args = parser.parse_args(argv)
    try:
        if args.command == 'compare':
            print(compare(json.loads(args.findings.read_text()), json.loads(args.exact.read_text()) if args.exact else None))
            return 0
        register()
        from .engine import run_test,author_results
        stage = Usd.Stage.Open(str(args.stage))
        if stage is None or stage.GetCompositionErrors():
            raise ValueError('Input stage did not compose')
        inputs = {Path(l.realPath).resolve() for l in stage.GetUsedLayers() if l.realPath}
        if args.output.resolve() in inputs:
            raise ValueError('Output must be separate from the input layer stack')
        if args.json and (args.json.resolve() in inputs or args.json.resolve() == args.output.resolve()):
            raise ValueError('JSON output must be separate from input and USD output layers')
        method = args.method or stage.GetPrimAtPath(args.test).GetAttribute('aeco:clash:method').Get()
        print('== stage: '+str(method)+' clash',flush=True)
        rows = run_test(stage,args.test,method=method)
        author_results(stage,rows,args.output)
        if args.json:
            args.json.write_text(json.dumps(rows,indent=2,sort_keys=True,allow_nan=False)+'\n')
        print(f'{len(rows)} {method} results; {sum(r["kind"] not in ("hard","clearance","touching") for r in rows)} unclassified')
        return 0
    except (ValueError,RuntimeError,OSError,NotImplementedError) as exc:
        print(str(exc),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
