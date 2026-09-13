#!/usr/bin/env python3
"""Run family gates and print N checks, M failed; NOT RUN never means PASS."""
import argparse
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
CORE=Path(os.environ.get('CORE_DIR',HERE.parent/'usdaeco-core'))
sys.path[:0]=[str(Path(os.environ.get('TOOLCHAIN_DIR',HERE.parent/'usdaeco-toolchain'))/'tools'),str(HERE/'tools'),str(HERE)]
from usdaeco_check import Report,can_apply,plugin_requires,registry_probe,validate_examples
from usdaeco_check.structure import check_structure
from usdaeco_check.example import check_example
from usdaeco_check.validation import run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-plugin',default=os.environ.get('CORE_PLUGIN_DIR',str(CORE/'out/plugins/usdAeco/resources')))
    args=parser.parse_args()
    report=Report()
    from usdaeco_clash.runtime import renderer,unavailable_reason
    renderer()
    print('== stage: registry',flush=True)
    if not report.add(plugin_requires([args.core_plugin,HERE/'usdAecoClash'])):
        return report.finish()
    from pxr import Plug,Usd,UsdValidation
    Plug.Registry().RegisterPlugins(str(CORE/'usdAecoValidators'))
    Plug.Registry().RegisterPlugins(str(HERE/'usdAecoClashValidators'))
    try:
        import usdAecoValidators
    except ImportError:
        report.check('core validators imported',False,'usdAecoValidators is not importable; include the core checkout in PYTHONPATH')
        return report.finish()
    registry=UsdValidation.ValidationRegistry()
    core_metadata=registry.GetValidatorMetadataForKeyword('UsdAecoValidators')
    report.check('core validators imported and loaded',len(core_metadata)==8 and all(registry.GetOrLoadValidatorByName(m.name) for m in core_metadata),f'{len(core_metadata)} registered core rules')
    metadata=registry.GetValidatorMetadataForKeyword('UsdAecoClashValidators')
    report.check('validator plugin listing',len(metadata)==4 and all(registry.GetOrLoadValidatorByName(m.name) for m in metadata),'4 clash rules')
    report.add(registry_probe([],['AecoClashTest','AecoClashResult','AecoPort']))
    report.add(can_apply([('AecoClashTest','CollectionAPI',True,'setA'),('AecoClashResult','AecoElementAPI',False)]))
    definition=Usd.SchemaRegistry().FindConcretePrimDefinition('AecoClashResult')
    report.check('derived measurements; editable review status',all(definition.GetPropertyMetadata('aeco:clash:'+p,'aecoDerived') is True for p in ('elements','kind','distance','volume','point','uncertainty','evidence')) and definition.GetPropertyMetadata('aeco:clash:status','aecoDerived') is not True)
    report.add(validate_examples(HERE/'usdAecoClash/examples',[],validators=[lambda stage:run(stage,['UsdAecoValidators','UsdAecoClashValidators'])]))
    print('== stage: structure',flush=True)
    for result in check_structure(HERE,deps=[args.core_plugin]):
        report.add(result)
    print('== stage: pinned example',flush=True)
    absent=unavailable_reason()
    if absent:
        report.not_run('fresh exact example and comparison',absent)
    elif not report.add(check_example(HERE/'examples/datacentre')):
        return report.finish()
    stage=Usd.Stage.Open(str(HERE/'examples/datacentre/result/example.usdc'))
    errors=run(stage,['UsdAecoValidators','UsdAecoClashValidators'])
    hard=[e for e in errors if e.GetType()==UsdValidation.ValidationErrorType.Error]
    report.check('published stage core and clash validation',not hard,f'{len(hard)} errors, {len(errors)-len(hard)} warnings; all 12 rules loaded')
    from usdaeco_clash.engine import run_test
    from usdaeco_clash.paths import resolve_test
    mesh=run_test(stage,resolve_test(stage,'Pinned'),method='mesh')
    report.check('mesh results',len(mesh)==3 and sorted(r['kind'] for r in mesh)==['clearance','hard','hard'],'3 mesh findings, 0 unclassified')
    if absent:
        report.not_run('exact distance, common volume and 5 mm decision',absent)
        return report.finish()
    findings=json.loads((HERE/'examples/datacentre/out/findings.json').read_text())
    comparisons={r['case']:r for r in findings if r['name']=='RouteComparison'}
    report.check('exact results',len(comparisons)==3 and sorted(r['exact']['kind'] for r in comparisons.values())==['clearance','hard','touching'],'3 measured pairs; 2 non-touching findings; 0 unclassified')
    report.check('through-wall common volume',comparisons['through-wall']['exact']['volume']>0 and comparisons['through-wall']['decided_by']=='both',f"{comparisons['through-wall']['exact']['volume']:.12g} cubic metres")
    near=comparisons['over-tray']
    report.check('5 mm decided only by exact',near['mesh']['verdict']=='undecidable' and near['decided_by']=='exact' and abs(near['exact']['distance']-.005)<=1e-6,
                 f"mesh band {near['mesh']['uncertainty']:.9g} m; exact band {near['exact']['uncertainty']:.9g} m")
    tangent=comparisons['tangent']
    report.check('false mesh penetration versus exact touching',tangent['mesh']['kind']=='hard' and tangent['mesh']['verdict']=='undecidable' and tangent['exact']['verdict']=='touching')
    report.check('source manifest witnesses',sum(r['name']=='ManifestWitness' and r['witness_matches'] for r in findings)==3,'axes, radii, sides, signed distances, bands and source witnesses asserted')
    studies=[r for r in findings if r['name']=='ExactDeflectionStudy']
    report.check('two exact-body deflection studies',len(studies)==2 and {r['requested'] for r in studies}=={.0001,.006} and len({tuple(r['triangles']) for r in studies})==2)
    report.check('comparison table matches expected', (HERE/'examples/datacentre/out/compare.md').read_bytes()==(HERE/'examples/datacentre/expected/compare.md').read_bytes())
    report.check('exact result layer published',(HERE/'examples/datacentre/result/layers/out/exact-results.usda').is_file())
    report.check('Route S wireframe rendered',(HERE/'examples/datacentre/renders/wireframe.png').is_file())
    return report.finish()


if __name__=='__main__':
    raise SystemExit(main())
