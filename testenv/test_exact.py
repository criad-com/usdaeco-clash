"""Native regression tests use committed exact bodies, never installed packages."""
import math
from pathlib import Path
import pytest
from pxr import Gf, Sdf, Usd, UsdGeom
from usdaeco_clash.engine import author_results, run_test
from usdaeco_clash.exact import ExactUnavailable, exact_bodies
from usdaeco_clash.runtime import unavailable_reason
from usdaeco_clash.comparison import compare, comparison_rows

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def stage():
    source=ROOT/'examples/datacentre/result/example.usdc'
    stage=Usd.Stage.Open(str(source))
    stage.SetEditTarget(stage.GetSessionLayer())
    return stage


@pytest.fixture
def native():
    reason=unavailable_reason()
    if reason:
        pytest.skip(reason)


def by_case(stage,rows):
    return {next(stage.GetPrimAtPath(p).GetAttribute('aeco:class:ifc:name').Get()
                 for p in row['elements'] if '/pipe_clash_' in p):row for row in rows}


def test_native_distances_volume_and_metadata(stage,native,tmp_path):
    before=stage.GetRootLayer().ExportToString()
    rows=run_test(stage,'/Clash/Pinned',method='exact')
    cases=by_case(stage,rows)
    hard=cases['pipe.clash.hard']
    assert hard['kind']=='hard' and hard['volume']==pytest.approx(math.pi*.03015**2*.15,abs=1e-12)
    assert hard['distance']==0 and math.copysign(1,hard['distance'])<0
    assert cases['pipe.clash.near']['distance']==pytest.approx(.005,abs=1e-9)
    assert cases['pipe.clash.tangent']['kind']=='touching' and cases['pipe.clash.tangent']['volume']==0
    for row in rows:
        assert row['uncertainty']==pytest.approx(sum(b['uncertainty'] for b in row['evidence']['bodies']))
        assert all(b['role']=='body' and b['approx']=='exact' and b['stamp'] for b in row['evidence']['bodies'])
    output=tmp_path/'results.usda'
    author_results(stage,rows,output)
    first=output.read_bytes()
    author_results(stage,rows,output)
    assert output.read_bytes()==first and stage.GetRootLayer().ExportToString()==before
    layer=Usd.Stage.Open(str(output))
    for row in rows:
        prim=layer.GetPrimAtPath(row['path'])
        assert prim.GetAttribute('aeco:clash:volume').HasAuthoredValueOpinion()
        assert not prim.GetAttribute('aeco:clash:status').HasAuthoredValueOpinion()


def test_world_placement_and_recheck(stage,native):
    original=run_test(stage,'/Clash/Pinned',method='exact')
    root=stage.GetDefaultPrim()
    UsdGeom.Xformable(root).AddTranslateOp(opSuffix='test').Set(Gf.Vec3d(9,12,3))
    rotated=UsdGeom.Xformable(root).AddRotateZOp(opSuffix='test');rotated.Set(30)
    changed=run_test(stage,'/Clash/Pinned',method='exact')
    assert [r['path'] for r in changed]==[r['path'] for r in original]
    for a,b in zip(changed,original):
        assert a['distance']==pytest.approx(b['distance'],abs=1e-9)
        assert a['volume']==pytest.approx(b['volume'],abs=1e-12)
    path=next(p for p in stage.Traverse() if p.GetAttribute('aeco:class:ifc:name').Get()=='pipe.clash.near').GetPath()
    UsdGeom.Xformable(stage.GetPrimAtPath(path)).AddTranslateOp(opSuffix='test').Set(Gf.Vec3d(0,0,1))
    assert len(run_test(stage,'/Clash/Pinned',method='exact'))==2


def test_nonuniform_transform_fails_loudly(stage,native):
    UsdGeom.Xformable(stage.GetDefaultPrim()).AddScaleOp(opSuffix='test').Set(Gf.Vec3f(2,1,1))
    with pytest.raises(RuntimeError,match='uniformly scaled'):
        run_test(stage,'/Clash/Pinned',method='exact')


@pytest.mark.parametrize('defect',['tolerance','approx','source','stamp'])
def test_invalid_exact_evidence(stage,defect):
    element=next(p for p in stage.Traverse() if p.GetAttribute('aeco:class:ifc:name').Get()=='pipe.clash.near')
    body=element.GetChild('BodyExact')
    prop=body.GetAttribute('aeco:derived:'+defect)
    prop.Set(0.0 if defect=='tolerance' else 'tessellated' if defect=='approx' else '')
    with pytest.raises(ValueError):
        exact_bodies(element)


def test_body_tolerance_precedence(stage):
    element=next(p for p in stage.Traverse() if p.GetAttribute('aeco:class:ifc:name').Get()=='pipe.clash.near')
    body=element.GetChild('BodyExact')
    body.CreateAttribute('aeco:body:tolerance',Sdf.ValueTypeNames.Double).Set(.00003)
    evidence,=exact_bodies(element)
    assert evidence['uncertainty']==.00003 and evidence['uncertainty_method']=='aeco:body:tolerance'


def test_runtime_absent_and_broken_are_distinct(stage,monkeypatch,tmp_path):
    monkeypatch.setenv('USD_SOLID_OCCT_RUNTIME',str(tmp_path/'absent'))
    with pytest.raises(ExactUnavailable,match='NOT RUN'):
        run_test(stage,'/Clash/Pinned',method='exact')
    monkeypatch.setenv('USD_SOLID_OCCT_RUNTIME',str(tmp_path))
    with pytest.raises(RuntimeError,match='paths.json'):
        run_test(stage,'/Clash/Pinned',method='exact')


def test_comparison_joins_pairs_and_keeps_unreported_distinct():
    def row(elements,method,kind,distance,band):
        return dict(elements=elements,kind=kind,distance=distance,uncertainty=band,
                    evidence=dict(method=method,band_decides=True))
    mesh=[row(['/A','/B'],'mesh','clearance',.005,.006),row(['/C','/D'],'mesh','hard',-.01,.001)]
    exact=[row(['/B','/A'],'exact','clearance',.005,.00002)]
    rows=comparison_rows(mesh,exact)
    assert rows[0]['decided_by']=='exact' and rows[0]['mesh']['verdict']=='undecidable'
    assert rows[1]['exact']['verdict']=='not reported'
    assert 'NOT RUN' not in compare(mesh,exact)
    assert 'NOT RUN' in compare(mesh)
    with pytest.raises(ValueError,match='one result per pair'):
        comparison_rows(mesh+mesh,exact)
