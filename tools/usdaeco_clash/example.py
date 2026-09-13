"""Pinned example hook; all derived opinions stay in separate layers."""
import json
import os
from pathlib import Path
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, Vt
from .engine import PREFIX,FALLBACKS,attr,run_test,author_results,bodies
from .geometry import measure
from .cli import compare
from .paths import camera_path, prepare_inputs, resolve_test, scope, study_root

CASES = {'pipe.clash.hard':'through-wall','pipe.clash.near':'over-tray','pipe.clash.tangent':'tangent'}


def source_elements(stage):
    names = set(CASES) | {'wall.l1.h.007','tray.void.ocorr.1'}
    result = {attr(p,'aeco:class:ifc:name'):p for p in stage.Traverse() if attr(p,'aeco:class:ifc:name') in names}
    if set(result) != names:
        raise ValueError('Pinned clash fixture needs three pipes, their wall and tray')
    return result


def stamp(mesh, element, role, tolerance, source, text):
    prim=mesh.GetPrim(); prim.ApplyAPI('AecoDerivedGeometryAPI')
    for key,value in {'source':attr(element,'aeco:id'),'role':role,'approx':'tessellated','stamp':text}.items():
        prim.CreateAttribute('aeco:derived:'+key,Sdf.ValueTypeNames.String if key in ('source','stamp') else Sdf.ValueTypeNames.Token,custom=False).Set(value)
    prim.CreateAttribute('aeco:derived:tolerance',Sdf.ValueTypeNames.Double,custom=False).Set(tolerance)
    prim.CreateRelationship('aeco:derived:from',custom=False).SetTargets([source])
    mesh.CreatePurposeAttr('proxy')


def create_mesh(stage,path,points,faces,color):
    mesh=UsdGeom.Mesh.Define(stage,path)
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*p) for p in points]))
    mesh.CreateFaceVertexCountsAttr([3]*len(faces))
    mesh.CreateFaceVertexIndicesAttr(faces.flatten().tolist())
    mesh.CreateSubdivisionSchemeAttr('none')
    mesh.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    return mesh


def derive(stage,out_dir):
    from .comparison import comparison_rows
    from .runtime import ROOT, configure, unavailable_reason
    from .example_source import export_bodies
    import sys
    import tempfile
    prepare_inputs(stage, out_dir)
    test_path = resolve_test(stage, 'Pinned')
    root = study_root(stage)
    elements=source_elements(stage)
    source_stage = os.environ.get('AECO_DATACENTRE_STAGE')
    source=Path(source_stage).with_name('dc.manifest.json') if source_stage else Path(os.environ['AECO_DATACENTRE_ROOT'])/'dist/clash/dc.manifest.json'
    manifest=json.loads(source.read_text())
    rows=run_test(stage,test_path,method='mesh')
    stage.GetRootLayer().subLayerPaths.insert(0,author_results(stage,rows,out_dir/'results.usda'))
    stage.SetMetadata('fallbackPrimTypes',{**stage.GetMetadata('fallbackPrimTypes'),**FALLBACKS})
    (out_dir/'mesh.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n')
    reason=unavailable_reason()
    exact=None
    findings=[{'name':'PinnedSourceCounts','counts':manifest['counts']}]
    # Verify the actual source census, not just a copied manifest number.
    assert sum(p.HasAPI('AecoElementAPI') for p in stage.Traverse()) == manifest['counts']['elements']
    assert sum(p.IsA(UsdGeom.Mesh) for p in stage.Traverse()) == manifest['counts']['meshes']
    if reason:
        findings.append(dict(name='ExactRuntime',status='NOT RUN',reason=reason))
    else:
        print('== stage: pinned exact export',flush=True)
        report=export_bodies(stage,elements,out_dir)
        stage.GetRootLayer().subLayerPaths[:0]=[str(out_dir/'exact.usda'),str(out_dir/'twins.usda')]
        fallbacks=stage.GetMetadata('fallbackPrimTypes');fallbacks['BrepArray']=Vt.TokenArray(['Xform']);stage.SetMetadata('fallbackPrimTypes',fallbacks)
        print('== stage: exact clash',flush=True)
        exact=run_test(stage,test_path,method='exact')
        stage.GetRootLayer().subLayerPaths.insert(0,author_results(stage,exact,out_dir/'exact-results.usda'))
        (out_dir/'exact.json').write_text(json.dumps(exact,indent=2,sort_keys=True)+'\n')
        findings.append(dict(name='ExactExport',selected=report['selected'],exact=report['exact'],failed=report['failed']))
    def case_for(pair):
        names=[attr(stage.GetPrimAtPath(p),'aeco:class:ifc:name') for p in pair]
        return next(CASES[n] for n in names if n in CASES)
    labels={tuple(sorted(r['elements'])):case_for(r['elements']) for r in rows}
    table=compare(rows,exact,reason,labels)
    (out_dir/'compare.md').write_text(table+'\n')
    for row in comparison_rows(rows,exact,reason):
        findings.append(dict(name='RouteComparison',case=case_for(row.pop('elements')),**row))
    # Assert all geometric witnesses and declarations against the pinned fixture.
    by_case={case_for(r['elements']):r for r in rows}
    exact_by_case={case_for(r['elements']):r for r in exact or []}
    for case in manifest['clash']['cases']:
        actual=by_case[CASES[case['id']]];source_mesh=case['mesh']
        assert abs(actual['distance']-source_mesh['signed_distance']) <= 1e-6
        assert abs(actual['uncertainty']-source_mesh['combined_deflection_band']) <= 1e-6
        from .geometry import closest_point, inside
        witness=np.asarray(source_mesh['witness'])
        partner=bodies(elements[case['partner']],UsdGeom.XformCache())[0]
        witness_gap=float(np.min(np.linalg.norm(closest_point(witness,partner.triangles)-witness,axis=1)))
        assert abs(witness_gap-abs(source_mesh['signed_distance'])) <= 1e-6
        assert inside(witness,partner.triangles) == (source_mesh['signed_distance']<0)
        pipe=bodies(elements[case['id']],UsdGeom.XformCache())[0]
        axis=np.asarray(case['axis']);direction=axis[1]-axis[0];length=np.linalg.norm(direction);direction/=length
        axial=(pipe.points-axis[0])@direction
        radial=np.linalg.norm(pipe.points-axis[0]-axial[:,None]*direction,axis=1)
        assert abs(float(axial.min()))<1e-6 and abs(float(axial.max())-length)<1e-6
        assert len(np.unique(np.round(pipe.points,7),axis=0)) == 2*case['sides']
        assert np.max(abs(radial-case['radius'])) <= actual['uncertainty']+1e-6
        if exact is not None:
            measured=exact_by_case[CASES[case['id']]]
            assert measured['kind']==case['exact']['verdict']
            if case['exact']['distance'] is not None:
                assert abs(measured['distance']-case['exact']['distance'])<=1e-6
            else:
                assert measured['volume']>0
        findings.append(dict(name='ManifestWitness',case=CASES[case['id']],mesh_verdict=source_mesh['verdict'],
                             radius=case['radius'],sides=case['sides'],axis=case['axis'],witness_matches=True))
    presentation=Usd.Stage.CreateNew(str(out_dir/'presentation.usda'))
    presentation.GetRootLayer().customLayerData={'aeco:clash:layer':'presentation only'}
    keep={p.GetPath() for p in elements.values()}
    for p in stage.Traverse():
        if p.IsA(UsdGeom.Gprim) and p.GetParent().GetPath() not in keep:
            UsdGeom.Imageable(presentation.OverridePrim(p.GetPath())).CreateVisibilityAttr('invisible')
    colors={'hard':(.92,.10,.055),'clearance':(1.,.62,.05),'touching':(.15,.7,.95)}
    for row in rows:
        for path in row['elements']:
            element=stage.GetPrimAtPath(path)
            color=colors[row['kind']] if attr(element,'aeco:class:ifc:name') in CASES else (.40,.44,.48)
            for p in element.GetChildren():
                if p.IsA(UsdGeom.Mesh):
                    mesh=UsdGeom.Mesh(presentation.OverridePrim(p.GetPath()))
                    mesh.CreateDisplayColorAttr([Gf.Vec3f(*color)])
                    mesh.CreateSubdivisionSchemeAttr('none')
                    # Show Route K in overview; retain exact twins for inspection.
                    mesh.CreateVisibilityAttr('invisible' if p.GetName()=='Body' else 'inherited')
    if exact is not None:
        sys.path.insert(0,str(Path(os.environ.get('AECO_SOLID_ROOT',ROOT.parent/'usdaeco-solid'))/'tools'))
        from usdaeco_solid.annotation import mesh_strokes
        from usdaeco_ifc.exact_common import mark
        for element in elements.values():
            curves=UsdGeom.BasisCurves(stage.GetPrimAtPath(element.GetPath().AppendChild('Edges')))
            display=mesh_strokes(presentation,curves,str(element.GetPath())+'/EdgeDisplay',radius=.001)
            mark(display.GetPrim(),attr(element,'aeco:id'),'wireframe','tessellated',.002,
                 'aeco-clash 0.2.0 edge display',curves.GetPath())
        wireframe=Usd.Stage.CreateNew(str(out_dir/'wireframe-view.usda'))
        wireframe.GetRootLayer().customLayerData={'aeco:clash:layer':'Route S wireframe view over exact mesh twins'}
        for element in elements.values():
            for child in element.GetChildren():
                if child.IsA(UsdGeom.Mesh) and attr(child,'aeco:derived:role')=='body':
                    UsdGeom.Imageable(wireframe.OverridePrim(child.GetPath())).CreateVisibilityAttr(
                        'inherited' if child.GetName()=='Body' else 'invisible')
        if root != Sdf.Path.absoluteRootPath:
            scope(wireframe.GetRootLayer(), '/Renders/clash')
        camera=UsdGeom.Camera.Define(wireframe,camera_path('wireframe', root))
        camera.CreateProjectionAttr('orthographic')
        camera.CreateHorizontalApertureAttr(28.)
        camera.CreateVerticalApertureAttr(17.5)
        camera.CreateClippingRangeAttr(Gf.Vec2f(.001,100))
        matrix=Gf.Matrix4d(1.).SetLookAt(Gf.Vec3d(25.5,-3.8,7.8),Gf.Vec3d(24,-1.5,6.86),Gf.Vec3d(0,0,1)).GetInverse()
        UsdGeom.Xformable(camera).AddTransformOp().Set(matrix)
        wireframe.GetRootLayer().Save()
        print('== stage: exact deflection study',flush=True)
        with tempfile.TemporaryDirectory(prefix='aeco-study-') as temp:
            directory=Path(temp);snapshot=directory/'source.usdc'
            stage.Flatten(addSourceFileComment=False).Export(str(snapshot))
            request=directory/'request.json'
            request.write_text(json.dumps(dict(stage=str(snapshot),bodies=[str(elements[n].GetPath())+'/BodyExact' for n in ('pipe.clash.near','tray.void.ocorr.1')])))
            studies=json.loads(configure().run_native(Path(__file__).with_name('study_worker.py'),request))
        study=Usd.Stage.CreateNew(str(out_dir/'deflection-study.usda'))
        study.GetRootLayer().customLayerData={'aeco:clash:layer':'exact-body tessellations at two deflections; presentation translations'}
        for index,record in enumerate(studies):
            triangles=[np.asarray(b['points'])[np.asarray(b['faces']).reshape(-1,3)] for b in record['bodies']]
            distance,_=measure(*triangles)
            findings.append(dict(name='ExactDeflectionStudy',study=record['study'],requested=record['requested'],
                                 distance=distance,triangles=[len(t) for t in triangles]))
            for b in record['bodies']:
                path=b['path'].rsplit('/',1)[0];element=stage.GetPrimAtPath(path)
                points=np.asarray(b['points'])+np.array([12.+index*6,0.,0.])
                inverse=UsdGeom.XformCache().GetLocalToWorldTransform(element).GetInverse()
                local=np.asarray([inverse.Transform(Gf.Vec3d(*p)) for p in points])
                mesh=create_mesh(study,path+'/Study'+record['study'].title(),local,np.asarray(b['faces']).reshape(-1,3),
                                 (1.,.62,.05) if element==elements['pipe.clash.near'] else (.4,.44,.48))
                stamp(mesh,element,'proxy',record['requested'],b['path'],'usdSolidOcct 0.1.0; linear deflection='+str(record['requested'])+' m; angular deflection=0.5 rad')
        study.GetRootLayer().Save()
        stage.GetRootLayer().subLayerPaths.insert(0,study.GetRootLayer().identifier)
    presentation.GetRootLayer().Save()
    stage.GetRootLayer().subLayerPaths.insert(0,presentation.GetRootLayer().identifier)
    from usdaeco_check.validation import run
    for error in run(stage,['UsdAecoClashValidators']):
        findings.append(dict(name=error.GetName(),severity=str(error.GetType()).split('.')[-1].lower(),
                             paths=[str(site.GetPrim().GetPath()) for site in error.GetSites()],message=error.GetMessage()))
    return findings
