#!/usr/bin/env python3
"""Regenerate this repository's selections and cameras from the pinned stage."""
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from pxr import Gf,Sdf,Usd,UsdGeom
from usdaeco_clash.cli import register
from usdaeco_clash.example import source_elements,CASES,TEST
from usdaeco_clash.engine import FALLBACKS


def main():
    register()
    stage=Usd.Stage.Open(str(Path(os.environ['AECO_DATACENTRE_ROOT'])/'dist/clash/dc.usda'))
    elements=source_elements(stage)
    inputs=Path(__file__).parent/'inputs'
    test_stage=Usd.Stage.CreateNew(str(inputs/'tests.usda'))
    test_stage.SetMetadata('fallbackPrimTypes',FALLBACKS)
    UsdGeom.Scope.Define(test_stage,'/Clash')
    test=test_stage.DefinePrim(TEST,'AecoClashTest')
    test.CreateAttribute('aeco:id',Sdf.ValueTypeNames.String).Set('d5d2aa31-76bb-5bd8-89c4-fd002370d2e4')
    test.CreateAttribute('aeco:clash:method',Sdf.ValueTypeNames.Token).Set('mesh')
    test.CreateAttribute('aeco:clash:tolerance',Sdf.ValueTypeNames.Double).Set(.001)
    test.CreateAttribute('aeco:clash:clearance',Sdf.ValueTypeNames.Double).Set(.01)
    for name,names in (('setA',CASES),('setB',('wall.l1.h.007','tray.void.ocorr.1'))):
        collection=Usd.CollectionAPI.Apply(test,name)
        collection.CreateExpansionRuleAttr('explicitOnly')
        collection.CreateIncludesRel().SetTargets([elements[n].GetPath() for n in names])
    test_stage.GetRootLayer().Save()
    cameras=Usd.Stage.CreateNew(str(inputs/'cameras.usda'))
    UsdGeom.Scope.Define(cameras,'/Renders')
    views=[('overview',(24,-2.4,14),(24,-2.4,6.8),6.2),
           ('fine',(36,-5,6.86),(36,-1.5,6.86),.26),
           ('coarse',(42,-5,6.86),(42,-1.5,6.86),.26)]
    for name,eye,target,width in views:
        cam=UsdGeom.Camera.Define(cameras,'/Renders/'+name)
        cam.CreateProjectionAttr('orthographic')
        cam.CreateHorizontalApertureAttr(width*10)
        cam.CreateVerticalApertureAttr(width*10*800/1280)
        cam.CreateClippingRangeAttr(Gf.Vec2f(.001,100))
        up=Gf.Vec3d(0,1,0) if name=='overview' else Gf.Vec3d(0,0,1)
        matrix=Gf.Matrix4d(1.).SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),up).GetInverse()
        UsdGeom.Xformable(cam).AddTransformOp().Set(matrix)
    cameras.GetRootLayer().Save()


if __name__=='__main__':
    main()
