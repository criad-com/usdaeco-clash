import numpy as np
import pytest
from usdaeco_clash.geometry import closest_point,segment_pairs,surface_distance,measure,inside,measured_deflection


def box(lo=(0,0,0),hi=(1,1,1)):
    points=np.array([[x,y,z] for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])],dtype=float)
    indices=np.array([[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]])
    return points[indices]


def test_point_face_edge_vertex():
    tri=np.array([[[0.,0,0],[2,0,0],[0,2,0]]])
    for p,q in [([.5,.5,1],[.5,.5,0]),([2,2,0],[1,1,0]),([-1,-1,0],[0,0,0])]:
        assert np.allclose(closest_point(p,tri)[0],q)


def test_skew_edge_witness():
    x,y=segment_pairs(np.array([-1.,0,0]),np.array([1.,0,0]),np.array([[0.,-1,1]]),np.array([[0.,1,1]]))
    assert np.allclose(x,[0,0,0]) and np.allclose(y,[0,0,1])


def test_triangles_intersect_and_coplanar():
    a=np.array([[[0.,0,0],[2,0,0],[0,2,0]]])
    b=np.array([[[.5,.5,-1],[.5,.5,1],[1,.5,0]]])
    assert surface_distance(a,b)[0]==0
    assert surface_distance(a,a+.1*np.array([1,1,0]))[0] < 1e-9


def test_containment_overlap_touch_gap():
    a=box()
    assert inside(np.array([.5,.5,.5]),a)
    assert not inside(np.array([1.,.5,.5]),a)
    assert measure(a,box((.2,.2,.2),(.8,.8,.8)))[0] < 0
    assert measure(a,box((.5,.5,.5),(1.5,1.5,1.5)))[0] < 0
    assert measure(a,box((1,0,0),(2,1,1)))[0] == 0
    assert measure(a,box((1.005,0,0),(2.005,1,1)))[0] == pytest.approx(.005)


def test_aabb_overlap_does_not_imply_triangle_hit():
    a=np.array([[[0.,0,0],[2,0,0],[0,2,0]]])
    b=np.array([[[1.5,1.5,0],[3,1.5,0],[1.5,3,0]]])
    assert surface_distance(a,b)[0] == pytest.approx(1/np.sqrt(2))


def test_unknown_deflection_refused():
    tetra=np.array([[[0.,0,0],[1,0,0],[0,1,0]],[[0,0,0],[1,0,0],[0,0,1]],[[0,0,0],[0,1,0],[0,0,1]],[[1,0,0],[0,1,0],[0,0,1]]])
    with pytest.raises(ValueError,match='Unknown tessellation'):
        measured_deflection(np.unique(tetra.reshape(-1,3),axis=0),tetra)


def test_coincident_closed_solids_are_hard_not_surface_touching():
    assert measure(box(),box())[0] == pytest.approx(-.5)
