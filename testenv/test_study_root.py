"""Scoped hooks, saved-stage consumers and source immutability on real fixtures."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pxr import Plug, Sdf, Usd, UsdGeom, UsdShade, UsdValidation

from usdaeco_clash import runtime
from usdaeco_clash.cli import main
from usdaeco_clash.engine import author_results, run_test
from usdaeco_clash.example import derive
from usdaeco_clash.paths import resolve_test, scope_layer, study_root

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/datacentre'


@pytest.fixture(autouse=True)
def hook_tools(monkeypatch):
    toolchain = Path(os.environ.get('TOOLCHAIN_DIR', ROOT.parent / 'usdaeco-toolchain'))
    monkeypatch.syspath_prepend(str(toolchain / 'tools'))
    Plug.Registry().RegisterPlugins(str(ROOT / 'usdAecoClashValidators'))


def compose(source, directory):
    base = Usd.Stage.Open(str(source))
    layer = Sdf.Layer.CreateNew(str(directory / 'stage.usda'))
    layer.TransferContent(base.GetRootLayer())
    layer.subLayerPaths = [str(EXAMPLE / 'inputs' / name) for name in ('tests.usda', 'cameras.usda')] + [str(source.resolve())]
    return Usd.Stage.Open(layer)


def assert_scoped(stage):
    assert not stage.GetCompositionErrors()
    project = stage.GetDefaultPrim().GetPath()
    assert {p.GetPath() for p in stage.GetPseudoRoot().GetAllChildren()} == {project, Sdf.Path('/Studies'), Sdf.Path('/Renders')}
    assert stage.GetPrimAtPath('/Studies').GetTypeName() == 'Scope'
    assert stage.GetPrimAtPath('/Studies/clash').GetTypeName() == 'Scope'
    assert resolve_test(stage) == Sdf.Path('/Studies/clash/Clash/Pinned')
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Camera):
            assert prim.GetPath().HasPrefix(Sdf.Path('/Renders/clash'))
        for rel in prim.GetRelationships():
            if rel.GetName() == 'material:binding':
                for target in rel.GetTargets():
                    assert stage.GetPrimAtPath(target).IsA(UsdShade.Material)
                    if target.name.startswith('m_'):
                        assert target.HasPrefix(Sdf.Path('/Studies/clash/ExactMaterials'))
        for attribute in prim.GetAttributes():
            for connection in attribute.GetConnections():
                assert stage.GetPropertyAtPath(connection)


def clash_errors(stage):
    from usdaeco_check.validation import run
    return run(stage, ['UsdAecoClashValidators'])


@pytest.mark.parametrize('value', ['', 'Studies/clash', '/Studies/clash.attr', '/Studies{variant=x}'])
def test_invalid_study_root(monkeypatch, value):
    monkeypatch.setenv('AECO_STUDY_ROOT', value)
    with pytest.raises(ValueError, match='absolute prim path'):
        study_root()


def test_saved_data_and_ambiguous_test_selection(monkeypatch):
    stage = Usd.Stage.CreateInMemory()
    test = stage.DefinePrim('/Studies/clash/Clash/Pinned', 'AecoClashTest')
    monkeypatch.setenv('AECO_STUDY_ROOT', '/Elsewhere')
    assert study_root(stage) == Sdf.Path('/Studies/clash')
    assert resolve_test(stage) == test.GetPath()
    assert resolve_test(stage, 'Pinned') == test.GetPath()
    stage.DefinePrim('/Studies/second/Clash/Pinned', 'AecoClashTest')
    with pytest.raises(ValueError, match='Select one'):
        resolve_test(stage, 'Pinned')
    assert resolve_test(stage, test.GetPath()) == test.GetPath()
    assert study_root(stage, test.GetPath()) == Sdf.Path('/Studies/clash')


@pytest.mark.parametrize('root', ['/', '/Studies/clash'])
def test_generated_inputs(tmp_path, monkeypatch, root):
    monkeypatch.setenv('AECO_STUDY_ROOT', root)
    monkeypatch.delenv('AECO_DATACENTRE_STAGE', raising=False)
    monkeypatch.setenv('AECO_DATACENTRE_ROOT', os.environ.get('AECO_DATACENTRE_ROOT', str(ROOT.parent / 'usdaeco-datacentre')))
    process = subprocess.run([sys.executable, str(EXAMPLE / 'generate_inputs.py'), '--out', str(tmp_path)],
                             env={k:v for k,v in os.environ.items() if k != 'PYTHONPATH'}, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    for name in ('tests.usda', 'cameras.usda'):
        if root == '/':
            assert (tmp_path / name).read_bytes() == (EXAMPLE / 'inputs' / name).read_bytes()
        layer = Sdf.Layer.FindOrOpen(str(tmp_path / name))
        original = layer.ExportToString()
        scope_layer(layer, '/')
        assert layer.ExportToString() == original
    if root != '/':
        stage = Usd.Stage.Open(str(tmp_path / 'tests.usda'))
        assert resolve_test(stage) == Sdf.Path(root + '/Clash/Pinned')
        assert stage.GetPrimAtPath('/Studies').GetTypeName() == 'Scope'
        cameras = Usd.Stage.Open(str(tmp_path / 'cameras.usda'))
        assert all(p.GetPath().HasPrefix(Sdf.Path('/Renders/clash')) for p in cameras.Traverse() if p.IsA(UsdGeom.Camera))


def test_scope_layer_paths_and_idempotence():
    stage = Usd.Stage.CreateInMemory()
    stage.DefinePrim('/ExactMaterials/M', 'Material').CreateAttribute('outputs:surface', Sdf.ValueTypeNames.Token)
    stage.DefinePrim('/__ExactPrototypes/P', 'Xform').CreateRelationship('material:binding').SetTargets(['/ExactMaterials/M'])
    instance = stage.DefinePrim('/Building/Instance', 'Xform')
    instance.GetReferences().AddInternalReference('/__ExactPrototypes/P')
    layer = stage.GetRootLayer()
    layer.customLayerData = {'paths': {'material': '/ExactMaterials/M', 'test': '/Clash/Pinned'}}
    stage.DefinePrim('/Clash/Pinned', 'AecoClashTest')
    scope_layer(layer, '/Studies/clash')
    assert layer.customLayerData['paths'] == {'material': '/Studies/clash/ExactMaterials/M', 'test': '/Studies/clash/Clash/Pinned'}
    assert instance.GetRelationship('material:binding').GetTargets() == [Sdf.Path('/Studies/clash/ExactMaterials/M')]
    assert not stage.GetCompositionErrors()
    original = layer.ExportToString()
    scope_layer(layer, '/Studies/clash')
    assert layer.ExportToString() == original


def test_full_delivery_hook_and_saved_cli(tmp_path, monkeypatch):
    source = Path(os.environ.get('AECO_FULL_DATACENTRE_STAGE', ROOT.parent / 'usdaeco-datacentre-0.5.2/dist/full/dc.usda'))
    if not source.is_file():
        pytest.skip('Set AECO_FULL_DATACENTRE_STAGE to the v0.5.2 full delivery')
    stage = compose(source, tmp_path)
    sources = {layer: layer.ExportToString() for layer in stage.GetUsedLayers() if layer != stage.GetRootLayer()}
    catalog = stage.GetDefaultPrim().GetChild('_TypeCatalog')
    assert catalog
    catalog_paths = {p.GetPath() for p in Usd.PrimRange(catalog, Usd.PrimAllPrimsPredicate)}
    monkeypatch.setenv('AECO_STUDY_ROOT', '/Studies/clash')
    monkeypatch.setenv('AECO_DATACENTRE_STAGE', str(source))
    # The full delivery's exact producer is separate from the old example recipe.
    with monkeypatch.context() as context:
        context.setattr(runtime, 'unavailable_reason', lambda: 'Exact producer retained separately for full delivery')
        findings = derive(stage, tmp_path)
    assert sum(row['name'] == 'ManifestWitness' for row in findings) == 3
    assert_scoped(stage)
    assert {p.GetPath() for p in Usd.PrimRange(catalog, Usd.PrimAllPrimsPredicate)} == catalog_paths
    # Exercise the same relocation API on retained exact/twin opinions as the suite.
    for name in ('exact.usda', 'twins.usda', 'exact-results.usda'):
        layer = Sdf.Layer.CreateNew(str(tmp_path / name))
        layer.TransferContent(Sdf.Layer.FindOrOpen(str(EXAMPLE / 'result/layers/out' / name)))
        scope_layer(layer, study_root(stage))
        layer.Save()
        stage.GetRootLayer().subLayerPaths.insert(0, layer.identifier)
    assert_scoped(stage)
    errors = clash_errors(stage)
    assert not [e for e in errors if e.GetType() == UsdValidation.ValidationErrorType.Error]
    assert all(site.GetPrim().GetPath().HasPrefix(Sdf.Path('/Studies/clash')) for e in errors for site in e.GetSites())
    assert sources == {layer: layer.ExportToString() for layer in sources}
    saved = tmp_path / 'saved.usdc'
    stage.Flatten(addSourceFileComment=False).Export(str(saved))
    monkeypatch.delenv('AECO_STUDY_ROOT')
    # A new process has neither hook globals nor the root setting.
    process = subprocess.run([sys.executable, str(ROOT / 'tools/run_clash.py'), 'run', str(saved),
                              '--output', str(tmp_path / 'cli.usda'), '--json', str(tmp_path / 'cli.json')],
                             env={k:v for k,v in os.environ.items() if k != 'PYTHONPATH'}, capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    rows = json.loads((tmp_path / 'cli.json').read_text())
    assert len(rows) == 3 and all(r['path'].startswith('/Studies/clash/Clash/Pinned/') for r in rows)
    monkeypatch.setenv('AECO_STUDY_ROOT', '/Unrelated')
    assert main(['run', str(saved), '--test', 'Pinned', '--output', str(tmp_path / 'named.usda')]) == 0
    assert (tmp_path / 'named.usda').read_bytes() == (tmp_path / 'cli.usda').read_bytes()
    if runtime.unavailable_reason():
        pytest.skip(runtime.unavailable_reason())
    exact = run_test(stage, resolve_test(stage), method='exact')
    assert sorted(r['kind'] for r in exact) == ['clearance', 'hard', 'touching']
    author_results(stage, exact, tmp_path / 'native.usda')
    assert all(r['path'].startswith('/Studies/clash/Clash/Pinned/') for r in exact)


def test_pinned_native_hook(tmp_path, monkeypatch):
    if runtime.unavailable_reason():
        pytest.skip(runtime.unavailable_reason())
    source = Path(os.environ.get('AECO_DATACENTRE_ROOT', ROOT.parent / 'usdaeco-datacentre')) / 'dist/clash/dc.usda'
    stage = compose(source, tmp_path)
    monkeypatch.setenv('AECO_STUDY_ROOT', '/Studies/clash')
    monkeypatch.setenv('AECO_DATACENTRE_ROOT', str(source.parents[2]))
    monkeypatch.delenv('AECO_DATACENTRE_STAGE', raising=False)
    findings = derive(stage, tmp_path)
    assert_scoped(stage)
    assert stage.GetPrimAtPath('/Studies/clash/ExactMaterials')
    assert sum(row['name'] == 'ExactExport' and row['exact'] == 5 and row['failed'] == 0 for row in findings) == 1
    assert sum(row['name'] == 'ExactDeflectionStudy' for row in findings) == 2
    assert (tmp_path / 'compare.md').read_bytes() == (EXAMPLE / 'expected/compare.md').read_bytes()
