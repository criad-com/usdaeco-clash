"""Double precision triangle queries. No bounding-box overlap is a verdict.

Meshes must be closed, manifold triangle surfaces. Distances include edge-edge
witnesses; inside tests use ray parity. Penetration is a sampled estimate, not
minimum translation distance or Boolean volume.
"""
from dataclasses import dataclass
import numpy as np

EPS = 1e-9


def closest_point(point, triangles):
    """Closest points on every triangle, including face, edge and vertex regions."""
    a, b, c = triangles.transpose(1, 0, 2)
    ab, ac = b - a, c - a
    n = np.cross(ab, ac)
    nn = np.einsum('ij,ij->i', n, n)
    projected = point - n * (np.einsum('ij,ij->i', point - a, n) / nn)[:, None]
    v = projected - a
    aa = np.einsum('ij,ij->i', ab, ab)
    bb = np.einsum('ij,ij->i', ac, ac)
    cc = np.einsum('ij,ij->i', ab, ac)
    va = np.einsum('ij,ij->i', v, ab)
    vc = np.einsum('ij,ij->i', v, ac)
    den = aa * bb - cc * cc
    u, w = (bb * va - cc * vc) / den, (aa * vc - cc * va) / den
    inside = (u >= 0) & (w >= 0) & (u + w <= 1)
    candidates = []
    for start, end in ((a, b), (b, c), (c, a)):
        edge = end - start
        t = np.clip(np.einsum('ij,ij->i', point - start, edge) /
                    np.einsum('ij,ij->i', edge, edge), 0, 1)
        candidates.append(start + t[:, None] * edge)
    candidates = np.stack(candidates, axis=1)
    distances = np.sum((candidates - point) ** 2, axis=2)
    result = candidates[np.arange(len(triangles)), np.argmin(distances, axis=1)]
    result[inside] = projected[inside]
    return result


def segment_pairs(p, q, starts, ends):
    """Closest witnesses between one segment and an array of segments."""
    u, v, w = q - p, ends - starts, p - starts
    a = np.dot(u, u)
    b, c = v @ u, np.sum(v * v, axis=1)
    d, e = w @ u, np.sum(v * w, axis=1)
    den = a * c - b * b
    s = np.divide(b * e - c * d, den, out=np.zeros_like(den), where=den > EPS ** 2)
    s = np.clip(s, 0, 1)
    t = (b * s + e) / c
    low, high = t < 0, t > 1
    s[low] = np.clip(-d[low] / a, 0, 1)
    s[high] = np.clip((b[high] - d[high]) / a, 0, 1)
    t = np.clip(t, 0, 1)
    return p + s[:, None] * u, starts + t[:, None] * v


def segment_hits(p, q, triangles):
    """Segment-triangle intersections (coplanarity handled by distance queries)."""
    a, b, c = triangles.transpose(1, 0, 2)
    direction = q - p
    e1, e2 = b - a, c - a
    h = np.cross(np.broadcast_to(direction, e2.shape), e2)
    det = np.sum(e1 * h, axis=1)
    inv = np.divide(1., det, out=np.zeros_like(det), where=np.abs(det) > EPS ** 2)
    offset = p - a
    u = np.sum(offset * h, axis=1) * inv
    cross = np.cross(offset, e1)
    v = cross @ direction * inv
    t = np.sum(e2 * cross, axis=1) * inv
    mask = (np.abs(det) > EPS ** 2) & (u >= -EPS) & (v >= -EPS) & (u + v <= 1 + EPS) & (t >= -EPS) & (t <= 1 + EPS)
    return p + t[mask, None] * direction


def surface_distance(a, b):
    """Triangle-triangle minimum, with explicit intersection and edge witnesses."""
    best, witness = float('inf'), None
    for source, target in ((a, b), (b, a)):
        for tri in source:
            for p, q in zip(tri, np.roll(tri, -1, axis=0)):
                hits = segment_hits(p, q, target)
                if len(hits):
                    return 0., hits[0]
                near = closest_point(p, target)
                ds = np.sum((near - p) ** 2, axis=1)
                i = np.argmin(ds)
                if ds[i] < best:
                    best, witness = ds[i], (near[i] + p) / 2
                for k in range(3):
                    x, y = segment_pairs(p, q, target[:, k], target[:, (k + 1) % 3])
                    ds = np.sum((x - y) ** 2, axis=1)
                    i = np.argmin(ds)
                    if ds[i] < best:
                        best, witness = ds[i], (x[i] + y[i]) / 2
    return float(np.sqrt(best)), witness


def inside(point, triangles):
    """Boundary is excluded; two deterministic rays guard edge coincidences."""
    near = closest_point(point, triangles)
    if np.min(np.linalg.norm(near - point, axis=1)) <= EPS:
        return False
    votes = []
    length = 4 * max(np.ptp(triangles.reshape(-1, 3), axis=0).max(), 1.)
    for direction in ((1., .37139067, .69474659), (.217823, 1., .532879)):
        hits = segment_hits(point, point + length * np.array(direction), triangles)
        distances = np.sort(np.linalg.norm(hits - point, axis=1))
        distinct = 0 if not len(distances) else 1 + np.count_nonzero(np.diff(distances) > EPS * 10)
        votes.append(bool(distinct % 2))
    if votes[0] != votes[1]:
        raise ValueError('Ambiguous mesh containment; refine or repair the surface')
    return votes[0]


def measure(a, b):
    """Signed gap / sampled interior depth and world-space witness."""
    gap, point = surface_distance(a, b)
    depth = 0.
    for source, target in ((a, b), (b, a)):
        clipped = []
        # Coincident closed shells have no strictly interior surface samples.
        # Try a volume seed, and only retain it if it is inside its own body.
        # Concave/hollow meshes may reject the centroid, so probe both sides of
        # face centers as a fallback; no assumption about winding is required.
        seed = source.reshape(-1, 3).mean(axis=0)
        if inside(seed, source):
            clipped.append(seed)
        elif gap <= EPS:
            scale = max(np.ptp(source.reshape(-1, 3), axis=0).max(), 1.)
            for tri in source:
                normal = np.cross(tri[1]-tri[0],tri[2]-tri[0])
                normal /= np.linalg.norm(normal)
                for sign in (-1,1):
                    candidate = tri.mean(axis=0) + sign*scale*1e-7*normal
                    if inside(candidate,source):
                        clipped.append(candidate)
        if gap <= EPS:
            # Midpoints between edge crossings catch thin walls traversed by long
            # triangles even when all vertices and face centroids lie outside.
            for tri in source:
                for p, q in zip(tri, np.roll(tri, -1, axis=0)):
                    hits = segment_hits(p, q, target)
                    if len(hits):
                        points = np.concatenate(([p], hits, [q]))
                        order = np.argsort((points-p) @ (q-p))
                        points = points[order]
                        clipped.extend((points[:-1]+points[1:])/2)
        samples = np.unique(np.concatenate((source.reshape(-1, 3), source.mean(axis=1),
                            np.asarray(clipped).reshape(-1, 3))), axis=0)
        for sample in samples:
            if inside(sample, target):
                value = np.min(np.linalg.norm(closest_point(sample, target) - sample, axis=1))
                if value > depth:
                    depth, point = float(value), sample
    return (-depth if depth > EPS else gap), point


def circular_fit(points):
    """Recognize a straight circular prism from two corresponding planar rings.

    Returns a fitted cylinder and measured maximum ring chord sagitta. This is
    conditional reconstruction, not evidence that the unknown source was round.
    """
    center = points.mean(axis=0)
    _, _, vh = np.linalg.svd(points - center, full_matrices=False)
    for axis in vh:
        axial = (points - center) @ axis
        lo, hi = axial.min(), axial.max()
        if hi - lo < EPS or np.max(np.minimum(abs(axial-lo), abs(axial-hi))) > 3e-6:
            continue
        ring = points[abs(axial-lo) < 3e-6]
        if len(ring) < 8 or len(ring) * 2 != len(points):
            continue
        helper = np.eye(3)[np.argmin(abs(axis))]
        u = np.cross(axis, helper); u /= np.linalg.norm(u)
        v = np.cross(axis, u)
        xy = np.stack(((ring-center) @ u, (ring-center) @ v), axis=1)
        coeff = np.linalg.lstsq(np.column_stack((2*xy, np.ones(len(xy)))), np.sum(xy*xy, axis=1), rcond=None)[0]
        offset = coeff[:2]
        radius = float(np.sqrt(coeff[2] + offset @ offset))
        all_xy = np.stack(((points-center) @ u, (points-center) @ v), axis=1) - offset
        residual = float(np.max(abs(np.linalg.norm(all_xy, axis=1) - radius)))
        if residual > max(3e-6, radius * 1e-4):
            continue
        angles = np.sort(np.arctan2(xy[:, 1]-offset[1], xy[:, 0]-offset[0]))
        step = float(np.max(np.diff(np.r_[angles, angles[0]+2*np.pi])))
        if step >= np.pi:
            continue
        return dict(center=center + offset[0]*u + offset[1]*v, axis=axis, u=u, v=v,
                    lo=float(lo), hi=float(hi), radius=radius,
                    error=radius*(1-np.cos(step/2))+residual)
    return None


def measured_deflection(points, triangles):
    fit = circular_fit(points)
    if fit:
        return float(fit['error']), 'measured ring chord sagitta plus circular-fit residual; assumes circular source'
    normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    directions = []
    for normal in normals:
        if not any(abs(normal @ d) > 1 - 1e-8 for d in directions):
            directions.append(normal)
    if len(directions) <= 3 and all(abs(a @ b) < 1e-6 for i, a in enumerate(directions) for b in directions[i+1:]):
        return 0., 'measured planar facets; assumes orthogonal planar source, excludes unknown curvature'
    raise ValueError('Unknown tessellation deflection: stamp the body tolerance; no defensible chordal fit')


@dataclass
class Body:
    path: str
    points: np.ndarray
    triangles: np.ndarray
    uncertainty: float
    evidence: dict

    @property
    def bounds(self):
        return self.points.min(axis=0), self.points.max(axis=0)


def aabb_distance(a, b):
    alo, ahi = a.bounds; blo, bhi = b.bounds
    return float(np.linalg.norm(np.maximum(np.maximum(alo-bhi, blo-ahi), 0)))
