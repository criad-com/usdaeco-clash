"""Run only in the bridge's Python: never load native libraries in wheel USD."""
import json
import math
from pathlib import Path
import sys
from pxr import Gf, Usd, UsdGeom, UsdSolid, UsdSolidOcct as Bridge
import _exact_native as Native


def build(stage, evidence, cache):
    prim = stage.GetPrimAtPath(evidence['body'])
    matrix = cache.GetLocalToWorldTransform(prim)
    axes = [Gf.Vec3d(*tuple(matrix[i])[:3]) for i in range(3)]
    scales = [axis.GetLength() for axis in axes]
    if (not all(math.isfinite(x) for row in matrix for x in row) or min(scales) <= 0
            or not all(math.isclose(s, scales[0], rel_tol=1e-10) for s in scales)
            or any(abs(Gf.Dot(axes[i], axes[j])) > 1e-10 * scales[0]**2 for i, j in ((0,1),(0,2),(1,2)))
            or any(abs(matrix[i][3]) > 1e-12 for i in range(3)) or abs(matrix[3][3]-1) > 1e-12):
        raise ValueError('Exact operations require rigid or uniformly scaled affine transforms')
    brep = UsdSolid.BrepArray(prim)
    # The bridge defaults to the first Brep. Reject ambiguous multi-body arrays.
    if len(brep.GetBrepRegionCountAttr().Get() or []) != 1:
        raise ValueError('Exact clash supports one Brep per BodyExact prim')
    shape = Bridge.Build(brep)
    if not Bridge.IsValid(shape) or not Bridge.SolidCount(shape):
        raise ValueError('Exact body did not build as a valid closed solid')
    shape = Native.Transform(shape, [float(x) for row in matrix for x in row])
    # Core tolerance is SI-fixed (metres), so placement scaling does not rewrite
    # the authored band; detect a transform that outgrows that declared bound.
    actual = Native.Inspect(shape)['tolerance']
    if actual > evidence['uncertainty'] * (1 + 1e-6):
        raise ValueError('World-space kernel tolerance exceeds the authored body tolerance')
    return shape


def main(request_path):
    request = json.loads(Path(request_path).read_text())
    stage = Usd.Stage.Open(request['stage'])
    if not stage or stage.GetCompositionErrors():
        raise ValueError('Exact input stage did not compose')
    cache = UsdGeom.XformCache()
    shapes = {e['body']: build(stage, e, cache) for group in request['bodies'].values() for e in group}
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'proxy', 'render'])
    rows = []
    for paths in request['pairs']:
        candidates = []
        for left in request['bodies'][paths[0]]:
            for right in request['bodies'][paths[1]]:
                a, b = shapes[left['body']], shapes[right['body']]
                separation = Bridge.Distance(a, b)
                volume = abs(Bridge.Volume(Bridge.Common(a, b)))
                if not all(math.isfinite(x) and x >= 0 for x in (separation, volume)):
                    raise ValueError('Kernel produced an invalid measurement')
                band = left['uncertainty'] + right['uncertainty']
                # Cubic tolerance removes numerical zero-volume slivers. This
                # is not a user clearance threshold or a penetration estimate.
                hard = volume > band**3
                kind = 'hard' if hard else 'touching' if separation <= request['tolerance'] else 'clearance'
                distance = -separation if hard else separation
                if not hard and distance > max(request['tolerance'], request['clearance']):
                    continue
                centers = [bounds.ComputeWorldBound(stage.GetPrimAtPath(p)).ComputeAlignedRange().GetMidpoint() for p in paths]
                point = (centers[0] + centers[1]) / 2
                decides = hard or distance - band > request['tolerance'] or distance + band <= request['tolerance']
                candidates.append(dict(elements=paths, kind=kind, distance=distance, volume=volume,
                    uncertainty=band, point=list(point), evidence=dict(method='exact', bodies=[left, right],
                        tolerance=request['tolerance'], band_decides=decides,
                        measurement='BRepAlgoAPI_Common volume; BRepExtrema_DistShapeShape separation, negative zero for overlap; no penetration depth',
                        point_method='midpoint of element bounds for camera framing; bridge does not expose extrema witnesses')))
        if candidates:
            # One finding per element pair: strongest common volume, else the
            # nearest body pair. Volume belongs only to the named evidence pair.
            rows.append(min(candidates, key=lambda r: (r['kind'] != 'hard', -r['volume'], r['distance'])))
    print(json.dumps(rows, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main(sys.argv[1])
