import json
import uuid
import numpy as np
import pytest
from pxr import Gf,Sdf,Usd,UsdGeom
from usdaeco_clash.engine import bodies,run_test,author_results,result_id,FALLBACKS
from usdaeco_clash.cli import compare
from usdaeco_clash.example import create_mesh
from test_geometry import box


def fixture():
    stage=Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(stage,1)
    UsdGeom.SetStageUpAxis(stage,'Z')
    stage.SetMetadata('fallbackPrimTypes',FALLBACKS)
    root=stage.DefinePrim('/World','Xform');stage.SetDefaultPrim(root)
    test=stage.DefinePrim('/World/Test','AecoClashTest')
    test.CreateAttribute('aeco:id',Sdf.ValueTypeNames.String).Set(str(uuid.uuid5(uuid.NAMESPACE_URL,'test')))
    for name,triangles in (('A',box()),('B',box((.5,.5,.5),(1.5,1.5,1.5)))):
        prim=stage.DefinePrim('/World/'+name,'Xform');prim.ApplyAPI('AecoElementAPI')
        prim.CreateAttribute('aeco:id',Sdf.ValueTypeNames.String).Set(str(uuid.uuid5(uuid.NAMESPACE_URL,name)))
        prim.ApplyAPI('AecoClassificationAPI','ifc')
        prim.CreateAttribute('aeco:class:ifc:code',Sdf.ValueTypeNames.String).Set('IfcBuildingElementProxy')
        mesh=create_mesh(stage,str(prim.GetPath())+'/Body',triangles.reshape(-1,3),np.arange(len(triangles)*3).reshape(-1,3),(.6,.4,.2))
        mesh.GetPrim().ApplyAPI('AecoDerivedGeometryAPI')
        for key,value in (('source',prim.GetAttribute('aeco:id').Get()),('role','body'),('approx','tessellated'),('stamp','synthetic planar body')):
            mesh.GetPrim().CreateAttribute('aeco:derived:'+key,Sdf.ValueTypeNames.String if key in ('source','stamp') else Sdf.ValueTypeNames.Token).Set(value)
    for name in ('setA','setB'):
        Usd.CollectionAPI.Apply(test,name).CreateIncludesRel().SetTargets(['/World/A','/World/B'])
    return stage,test


def test_symmetry_self_pair_and_ids():
    stage,test=fixture();rows=run_test(stage,test.GetPath())
    assert len(rows)==1 and rows[0]['kind']=='hard'
    assert result_id('t','a','b')==result_id('t','b','a')
    assert result_id('other','a','b')!=result_id('t','a','b')
    for name in ('setA','setB'):
        Usd.CollectionAPI(test,name).CreateIncludesRel().SetTargets(['/World/B','/World/A'])
    assert run_test(stage,test.GetPath())==rows


def test_check_overlay_recheck(tmp_path):
    stage,test=fixture();original=stage.GetRootLayer().ExportToString()
    rows=run_test(stage,test.GetPath())
    output=tmp_path/'results.usda'
    author_results(stage,rows,output)
    first=output.read_bytes()
    author_results(stage,rows,output)
    assert output.read_bytes()==first
    assert stage.GetRootLayer().ExportToString()==original
    edit=Sdf.Layer.CreateAnonymous('intent.usda')
    stage.GetRootLayer().subLayerPaths.insert(0,edit.identifier)
    with Usd.EditContext(stage,edit):
        UsdGeom.Xformable(stage.GetPrimAtPath('/World/B')).AddTranslateOp().Set(Gf.Vec3d(3,0,0))
    assert run_test(stage,test.GetPath())==[]
    stage.MuteLayer(edit.identifier)
    assert run_test(stage,test.GetPath())==rows
    stage.GetRootLayer().subLayerPaths.insert(0,str(output))
    result=stage.GetPrimAtPath(rows[0]['path'])
    assert not result.GetAttribute('aeco:clash:volume').HasAuthoredValueOpinion()
    assert stage.GetPrimAtPath(rows[0]['path']+'/Camera').IsA(UsdGeom.Camera)
    review=Sdf.Layer.CreateAnonymous('review.usda')
    stage.GetRootLayer().subLayerPaths.insert(0,review.identifier)
    with Usd.EditContext(stage,review):
        result.GetAttribute('aeco:clash:status').Set('reviewed')
    author_results(stage,rows,output)
    assert result.GetAttribute('aeco:clash:status').Get()=='reviewed'


@pytest.mark.parametrize('key,value',[('tolerance',-1),('clearance',float('nan')),('clearance',float('inf'))])
def test_invalid_drivers(key,value):
    stage,test=fixture();test.CreateAttribute('aeco:clash:'+key,Sdf.ValueTypeNames.Double).Set(value)
    with pytest.raises(ValueError,match='finite'):
        run_test(stage,test.GetPath())


def test_absent_exact_evidence_is_not_passed():
    stage,test=fixture()
    text=compare(run_test(stage,test.GetPath()))
    assert 'NOT RUN' in text and '| exact' in text
    test.CreateAttribute('aeco:clash:method',Sdf.ValueTypeNames.Token).Set('exact')
    from usdaeco_clash.runtime import unavailable_reason
    expected = 'NOT RUN' if unavailable_reason() else 'no exact body'
    with pytest.raises((RuntimeError, ValueError),match=expected):
        run_test(stage,test.GetPath())


def test_body_stamp_precedence_and_invalid_tolerance():
    stage,test=fixture();body=stage.GetPrimAtPath('/World/A/Body')
    body.CreateAttribute('aeco:body:tolerance',Sdf.ValueTypeNames.Double).Set(.006)
    assert bodies(body.GetParent(),UsdGeom.XformCache())[0].uncertainty==.006
    body.GetAttribute('aeco:body:tolerance').Set(float('nan'))
    with pytest.raises(ValueError,match='tolerance'):
        run_test(stage,test.GetPath())


def test_missing_identity_and_missing_body():
    stage,test=fixture()
    stage.GetPrimAtPath('/World/A').GetAttribute('aeco:id').Set('')
    with pytest.raises(ValueError,match='aeco:id'):
        run_test(stage,test.GetPath())
    stage,test=fixture();stage.RemovePrim('/World/A/Body')
    with pytest.raises(ValueError,match='no supported body'):
        run_test(stage,test.GetPath())


def test_nested_original_does_not_hide_parent_exact_twin():
    stage,test=fixture()
    element=stage.GetPrimAtPath('/World/A')
    stage.DefinePrim('/World/A/BodyExact','BrepArray')
    element.GetChild('Body').CreateRelationship('aeco:derived:from').SetTargets(['/World/A/BodyExact'])
    child=stage.DefinePrim('/World/A/Child','Xform')
    child.ApplyAPI('AecoElementAPI')
    stage.DefinePrim('/World/A/Child/Body','Mesh')
    selected=bodies(element,UsdGeom.XformCache())
    assert len(selected)==1 and selected[0].path=='/World/A/Body'


def test_invalid_mesh_and_units():
    stage,test=fixture();body=UsdGeom.Mesh(stage.GetPrimAtPath('/World/A/Body'))
    body.CreateFaceVertexCountsAttr([4])
    with pytest.raises(ValueError,match='triangle topology'):
        run_test(stage,test.GetPath())
    stage,test=fixture();UsdGeom.SetStageMetersPerUnit(stage,.001)
    with pytest.raises(ValueError,match='metres'):
        run_test(stage,test.GetPath())


def test_long_edges_through_thin_wall():
    from usdaeco_clash.geometry import measure
    wall=box((-.05,-1,-1),(.05,1,1))
    crossing=box((-2,-.05,-.05),(2,.05,.05))
    assert measure(wall,crossing)[0]<-.01


def test_converter_stamp_units_and_core_zero_unknown():
    stage,test=fixture();body=stage.GetPrimAtPath('/World/A/Body')
    body.CreateAttribute('aeco:derived:tolerance',Sdf.ValueTypeNames.Double).Set(0)
    body.GetAttribute('aeco:derived:stamp').Set('tessellator deflection=3 mm; triangle mesh')
    measured=bodies(body.GetParent(),UsdGeom.XformCache())[0]
    assert measured.uncertainty==pytest.approx(.003)
    assert measured.evidence['uncertainty_method'].startswith('converter stamp')


def test_dangling_selection_fails_even_with_valid_elements():
    stage,test=fixture()
    Usd.CollectionAPI(test,'setA').CreateIncludesRel().SetTargets(['/World/A','/Missing'])
    with pytest.raises(ValueError,match='Dangling'):
        run_test(stage,test.GetPath())


def test_controlled_small_penetration_is_covered_by_band():
    stage,test=fixture()
    triangles=box((.9988,-.1,-.1),(2,1.1,1.1))
    UsdGeom.Mesh(stage.GetPrimAtPath('/World/B/Body')).GetPointsAttr().Set([Gf.Vec3f(*p) for p in triangles.reshape(-1,3)])
    for name in ('A','B'):
        stage.GetPrimAtPath('/World/'+name+'/Body').CreateAttribute('aeco:body:tolerance',Sdf.ValueTypeNames.Double).Set(.003)
    row,=run_test(stage,test.GetPath())
    assert row['kind']=='hard'
    assert row['distance']==pytest.approx(-.0012,abs=1e-7)
    assert row['uncertainty']>=abs(row['distance'])
