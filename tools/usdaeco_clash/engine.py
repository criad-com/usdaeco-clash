"""Collection-selected mesh checks and deterministic derived result overlays."""
import json
import math
from pathlib import Path
import re
import uuid
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, Vt
from .geometry import Body, aabb_distance, measure, measured_deflection

PREFIX = 'aeco:clash:'
FALLBACKS = {'AecoClashTest': Vt.TokenArray(['Scope']), 'AecoClashResult': Vt.TokenArray(['Scope'])}


def attr(prim, name, default=None):
    value = prim.GetAttribute(name).Get()
    return default if value is None else value


def bodies(element, cache):
    """Read derived body meshes; the role also accepts older exports named Geom."""
    found = []
    candidates = [p for p in Usd.PrimRange(element) if p.IsA(UsdGeom.Mesh)
                  and (attr(p,'aeco:derived:role','') == 'body' or p.GetName() == 'Body')]
    owned = []
    for prim in candidates:
        parent = prim.GetParent()
        while parent != element and parent and not parent.HasAPI('AecoElementAPI'):
            parent = parent.GetParent()
        if parent == element:
            owned.append(prim)
    candidates = owned
    originals = [p for p in candidates if not any(
        element.GetStage().GetPrimAtPath(target).GetTypeName() == 'BrepArray'
        for target in p.GetRelationship('aeco:derived:from').GetTargets()
        if element.GetStage().GetPrimAtPath(target))]
    # Keep the Route K input when an independently exported exact twin is
    # composed alongside it. A twin-only stage remains a valid mesh input.
    for prim in originals or candidates:
        if not prim.IsA(UsdGeom.Mesh):
            continue
        if attr(prim, 'aeco:derived:role', '') != 'body' and prim.GetName() != 'Body':
            continue
        mesh = UsdGeom.Mesh(prim)
        points = np.asarray(mesh.GetPointsAttr().Get(), dtype=float)
        counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get(), dtype=int)
        indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=int)
        if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all() or not len(counts):
            raise ValueError('Body has invalid points or no faces: ' + str(prim.GetPath()))
        if np.any(counts != 3) or len(indices) != 3*len(counts) or np.any(indices < 0) or np.any(indices >= len(points)):
            raise ValueError('Body requires valid triangle topology: ' + str(prim.GetPath()))
        if mesh.GetHoleIndicesAttr().Get():
            raise ValueError('Body holes are unsupported: ' + str(prim.GetPath()))
        if mesh.GetSubdivisionSchemeAttr().HasAuthoredValueOpinion() and mesh.GetSubdivisionSchemeAttr().Get() != 'none':
            raise ValueError('Body must be an explicit tessellation (subdivisionScheme = none)')
        matrix = cache.GetLocalToWorldTransform(prim)
        points = np.asarray([matrix.Transform(Gf.Vec3d(*p)) for p in points])
        tris = points[indices.reshape(-1, 3)]
        if np.any(np.linalg.norm(np.cross(tris[:,1]-tris[:,0], tris[:,2]-tris[:,0]), axis=1) < 1e-15):
            raise ValueError('Body has degenerate triangles')
        # Weld coincident points for the manifold check; exporters may split normals.
        _, weld = np.unique(points, axis=0, return_inverse=True)
        faces = weld[indices.reshape(-1, 3)]
        edges = np.sort(np.concatenate((faces[:,[0,1]], faces[:,[1,2]], faces[:,[2,0]])), axis=1)
        _, incidence = np.unique(edges, axis=0, return_counts=True)
        if np.any(incidence != 2):
            raise ValueError('Body must be a closed manifold surface')
        if not np.isfinite(points).all():
            raise ValueError('Body transform produces non-finite points')
        stamp = attr(prim, 'aeco:derived:stamp', '')
        bound, method = None, None
        for key in ('aeco:body:tolerance', 'aeco:derived:tolerance'):
            prop = prim.GetAttribute(key)
            if prop and prop.HasAuthoredValueOpinion():
                bound, method = prop.Get(), key
                if bound == 0:
                    bound, method = None, None  # Core zero means unknown.
                    continue
                break
        if bound is None:
            match = re.search(r'(?:deflection|tolerance)\s*[=:]\s*([0-9.eE+-]+)\s*(mm|m)?(?=\s|[;,)]|$)', stamp)
            if match:
                bound = float(match[1]) * (.001 if match[2] == 'mm' else 1.)
                method = 'converter stamp (converted to metres)'
                if bound == 0:
                    bound, method = None, None
        if bound is None:
            bound, method = measured_deflection(points, tris)
        if not isinstance(bound, (int, float)) or not math.isfinite(bound) or bound < 0:
            raise ValueError('Invalid body tolerance')
        evidence = dict(body=str(prim.GetPath()), role=attr(prim,'aeco:derived:role','body'),
                        approx=attr(prim,'aeco:derived:approx','unspecified'), stamp=stamp,
                        uncertainty=float(bound), uncertainty_method=method)
        found.append(Body(str(prim.GetPath()), points, tris, float(bound), evidence))
    if not found:
        raise ValueError('Selected element has no supported body mesh: ' + str(element.GetPath()))
    return found


def selection(test, name):
    collection = Usd.CollectionAPI(test, name)
    for path in collection.GetIncludesRel().GetTargets():
        if not path.IsPrimPath() or not test.GetStage().GetPrimAtPath(path):
            raise ValueError('Dangling or non-prim collection inclusion: ' + str(path))
    query = collection.ComputeMembershipQuery()
    paths = Usd.CollectionAPI.ComputeIncludedPaths(query, test.GetStage())
    selected = []
    for path in sorted(paths):
        prim = test.GetStage().GetPrimAtPath(path)
        if prim and prim.HasAPI('AecoElementAPI'):
            selected.append(prim)
    if not selected:
        raise ValueError('Empty element selection: ' + name)
    return selected


def result_id(test_id, a, b):
    return 'Result_' + uuid.uuid5(uuid.NAMESPACE_URL, json.dumps([test_id, *sorted((a, b))], separators=(',', ':'))).hex


def test_inputs(stage, test_path):
    if not math.isclose(UsdGeom.GetStageMetersPerUnit(stage), 1.) or UsdGeom.GetStageUpAxis(stage) != 'Z':
        raise ValueError('Clash requires a metres / Z-up stage')
    test = stage.GetPrimAtPath(test_path)
    if not test or test.GetTypeName() != 'AecoClashTest':
        raise ValueError('Expected an AecoClashTest prim')
    tolerance, clearance = (float(attr(test, PREFIX+k, v)) for k,v in (('tolerance',.001),('clearance',0.)))
    if not all(math.isfinite(v) and v >= 0 for v in (tolerance, clearance)):
        raise ValueError('Test tolerance and clearance must be finite and non-negative')
    test_id = attr(test, 'aeco:id', '')
    if not test_id:
        raise ValueError('Test needs a stable aeco:id')
    a, b = selection(test, 'setA'), selection(test, 'setB')
    elements = {str(p.GetPath()): p for p in a+b}
    identities = [attr(p,'aeco:id','') for p in elements.values()]
    if not all(identities) or len(set(identities)) != len(identities):
        raise ValueError('Selected elements need distinct nonempty aeco:id values')
    return test, tolerance, clearance, test_id, a, b, elements


def run_test(stage, test_path, method=None):
    test = stage.GetPrimAtPath(test_path)
    method = method or attr(test, PREFIX+'method', 'mesh')
    if method == 'exact':
        from .exact import run_exact
        return run_exact(stage, test_path)
    if method != 'mesh':
        raise ValueError('Unknown clash method: ' + method)
    test, tolerance, clearance, test_id, a, b, elements = test_inputs(stage, test_path)
    cache = UsdGeom.XformCache()
    meshes = {path:bodies(p, cache) for path,p in elements.items()}
    results, seen = [], set()
    for first in a:
        for second in b:
            paths = tuple(sorted((str(first.GetPath()),str(second.GetPath()))))
            if paths[0] == paths[1] or paths in seen:
                continue
            seen.add(paths)
            best = None
            for left in meshes[paths[0]]:
                for right in meshes[paths[1]]:
                    if aabb_distance(left, right) > max(clearance, tolerance):
                        continue
                    distance, point = measure(left.triangles, right.triangles)
                    if best is None or distance < best[0]:
                        best = distance, point, left, right
            if best is None or best[0] > max(clearance, tolerance):
                continue
            distance, point, left, right = best
            kind = 'hard' if distance < -tolerance else 'touching' if distance <= tolerance else 'clearance'
            uncertainty = left.uncertainty + right.uncertainty
            ids = [attr(elements[p], 'aeco:id') for p in paths]
            results.append(dict(path=str(test.GetPath())+'/'+result_id(test_id,*ids), elements=list(paths),
                                kind=kind, distance=float(distance), point=[float(v) for v in point],
                                uncertainty=uncertainty,
                                evidence=dict(method='mesh', bodies=[left.evidence,right.evidence], tolerance=tolerance,
                                    measurement='triangle surface gap; negative maximum sampled interior depth (vertices, centroids and clipped edge intervals), not minimum translation distance',
                                    band_decides=abs(distance)>uncertainty)))
    return sorted(results, key=lambda r:r['path'])


def frame_camera(stage, path, center, span):
    camera = UsdGeom.Camera.Define(stage, path)
    target = Gf.Vec3d(*center)
    distance = max(float(span)*1.8, .2)
    eye = target + Gf.Vec3d(distance, -distance, distance)
    matrix = Gf.Matrix4d(1.).SetLookAt(eye,target,Gf.Vec3d(0,0,1)).GetInverse()
    UsdGeom.Xformable(camera).AddTransformOp().Set(matrix)
    camera.CreateFocalLengthAttr(45.)
    camera.CreateClippingRangeAttr(Gf.Vec2f(.001, max(100., distance*12)))
    return camera


def author_results(stage, results, output):
    """Write a fresh derived layer. Composing it is a caller-owned operation."""
    path = Path(output)
    path.parent.mkdir(parents=True,exist_ok=True)
    existing = Sdf.Layer.Find(str(path.resolve()))
    if existing:
        existing.Clear()
        overlay = Usd.Stage.Open(existing)
    else:
        overlay = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(overlay,1.)
    UsdGeom.SetStageUpAxis(overlay,'Z')
    overlay.SetMetadata('fallbackPrimTypes',FALLBACKS)
    overlay.GetRootLayer().customLayerData = {'aeco:clash:layer':'derived clash results'}
    types = {'kind':Sdf.ValueTypeNames.Token,'distance':Sdf.ValueTypeNames.Double,
             'point':Sdf.ValueTypeNames.Point3d,'uncertainty':Sdf.ValueTypeNames.Double,'evidence':Sdf.ValueTypeNames.String,
             'volume':Sdf.ValueTypeNames.Double}
    for row in results:
        overlay.OverridePrim(Sdf.Path(row['path']).GetParentPath())
        prim = overlay.DefinePrim(row['path'],'AecoClashResult')
        prim.CreateRelationship(PREFIX+'elements',custom=False).SetTargets(row['elements'])
        for key, value_type in types.items():
            if key not in row:
                continue
            value = json.dumps(row[key],sort_keys=True,separators=(',',':')) if key=='evidence' else row[key]
            if key == 'point':
                value = Gf.Vec3d(*value)
            prim.CreateAttribute(PREFIX+key,value_type,custom=False).Set(value)
        frame_camera(overlay,row['path']+'/Camera',row['point'],.5)
    overlay.GetRootLayer().Save()
    return str(path.resolve())
