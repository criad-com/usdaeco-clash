"""Select exact representations and delegate kernel work across the ABI boundary."""
import json
import math
from pathlib import Path
import tempfile
from pxr import Usd, UsdGeom
from .engine import attr, result_id, test_inputs
from .runtime import configure, unavailable_reason


class ExactUnavailable(RuntimeError):
    """Only an absent optional runtime qualifies as NOT RUN."""


def exact_bodies(element):
    found = []
    for prim in Usd.PrimRange(element, Usd.TraverseInstanceProxies()):
        if prim.GetTypeName() != 'BrepArray':
            continue
        parent = prim.GetParent()
        while parent != element and parent and not parent.HasAPI('AecoElementAPI'):
            parent = parent.GetParent()
        if parent != element:
            continue
        if attr(prim, 'aeco:derived:role') != 'body' or attr(prim, 'aeco:derived:approx') != 'exact':
            raise ValueError('BrepArray must declare role body and approximation exact')
        if attr(prim, 'aeco:derived:source') != attr(element, 'aeco:id'):
            raise ValueError('Exact body source does not match its element identity')
        key = 'aeco:body:tolerance'
        prop = prim.GetAttribute(key)
        if not prop or not prop.HasAuthoredValueOpinion():
            key = 'aeco:derived:tolerance'
        tolerance = attr(prim, key)
        if not isinstance(tolerance, (int, float)) or not math.isfinite(tolerance) or tolerance <= 0:
            raise ValueError('Exact body requires a positive finite kernel tolerance')
        stamp = attr(prim, 'aeco:derived:stamp', '')
        if not stamp:
            raise ValueError('Exact body requires a producer stamp')
        found.append(dict(body=str(prim.GetPath()), role='body', approx='exact', stamp=stamp,
                          uncertainty=tolerance, uncertainty_method=key))
    if not found:
        raise ValueError('Selected element has no exact body: ' + str(element.GetPath()))
    return found


def run_exact(stage, test_path):
    reason = unavailable_reason()
    if reason:
        raise ExactUnavailable('Exact engine NOT RUN: ' + reason)
    test, tolerance, clearance, test_id, a, b, elements = test_inputs(stage, test_path)
    bodies = {path: exact_bodies(p) for path, p in elements.items()}
    pairs = sorted({tuple(sorted((str(x.GetPath()), str(y.GetPath()))))
                    for x in a for y in b if x != y})
    request = dict(bodies=bodies, pairs=pairs, tolerance=tolerance, clearance=clearance)
    with tempfile.TemporaryDirectory(prefix='aeco-clash-') as temp:
        directory = Path(temp)
        request['stage'] = str(directory / 'source.usdc')
        stage.Flatten(addSourceFileComment=False).Export(request['stage'])
        request_path = directory / 'request.json'
        request_path.write_text(json.dumps(request, allow_nan=False))
        output = configure().run_native(Path(__file__).with_name('exact_worker.py'), request_path)
        measured = json.loads(output)
    rows = []
    for row in measured:
        ids = [attr(elements[p], 'aeco:id') for p in row['elements']]
        row['path'] = str(test.GetPath()) + '/Exact' + result_id(test_id, *ids)
        rows.append(row)
    return sorted(rows, key=lambda r: r['path'])
