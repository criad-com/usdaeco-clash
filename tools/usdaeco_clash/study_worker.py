"""Tessellate the same exact bodies at two requested linear deflections."""
import json
from pathlib import Path
import sys
from pxr import Usd, UsdGeom, UsdSolid, UsdSolidOcct as Bridge
import _exact_native as Native


def main(request_path):
    request = json.loads(Path(request_path).read_text())
    stage = Usd.Stage.Open(request['stage'])
    cache = UsdGeom.XformCache()
    rows = []
    for name, deflection in (('fine',.0001), ('coarse',.006)):
        row = dict(study=name, requested=deflection, bodies=[])
        for path in request['bodies']:
            prim = stage.GetPrimAtPath(path)
            shape = Bridge.Build(UsdSolid.BrepArray(prim))
            shape = Native.Transform(shape, [float(x) for r in cache.GetLocalToWorldTransform(prim) for x in r])
            mesh = Bridge.Tessellate(shape, deflection, .5)
            row['bodies'].append(dict(path=path, points=[list(p) for p in mesh.points],
                                      faces=list(mesh.faceVertexIndices)))
        rows.append(row)
    print(json.dumps(rows, allow_nan=False))


if __name__ == '__main__':
    main(sys.argv[1])
