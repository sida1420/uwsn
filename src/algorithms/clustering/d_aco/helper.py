import math
import numpy
"""
    Only PRO can understand this file
"""


def _clipped_quarter_disk_area(rho, p, q):
    """Area of the quarter disk (radius rho, center at origin, x,y >= 0)
    clipped to the rectangle [0,p] x [0,q]."""
    if rho <= 0:
        return 0.0
    F = lambda x: 0.5 * (x * math.sqrt(max(rho*rho - x*x, 0.0))
                         + rho*rho * math.asin(min(x / rho, 1.0)))
    xm = min(p, rho)
    if q >= rho:
        return F(xm)
    x0 = math.sqrt(rho*rho - q*q)      # where the circle drops below height q
    if x0 >= xm:
        return q * xm
    return q * x0 + F(xm) - F(x0)

def _octant(p, q, s, r, n=200):
    """Volume of sphere (center at origin, radius r) inside [0,p]x[0,q]x[0,s]."""
    if p <= 0 or q <= 0 or s <= 0 or r <= 0:
        return 0.0
    zmax = min(s, r)
    # split z where the circle crosses the box sides/corner
    cuts = {0.0, zmax}
    for d in (p, q, math.hypot(p, q)):
        if d < r:
            z = math.sqrt(r*r - d*d)
            if 0 < z < zmax:
                cuts.add(z)
    cuts = sorted(cuts)

    f = lambda z: _clipped_quarter_disk_area(math.sqrt(max(r*r - z*z, 0.0)), p, q)
    total = 0.0
    for a, b in zip(cuts, cuts[1:]):   # Simpson on each smooth piece
        h = (b - a) / n
        acc = f(a) + f(b)
        for i in range(1, n):
            acc += f(a + i*h) * (4 if i % 2 else 2)
        total += acc * h / 3
    return total

def covered_volume(cube_min, cube_max, center, r):
    """Volume of the axis-aligned cube covered by the sphere.
    Returns 0 if the center is outside (on a face/edge/corner counts as inside)."""
    for lo, hi, c in zip(cube_min, cube_max, center):
        if c < lo or c > hi:
            return 0.0
    dists = [(c - lo, hi - c) for lo, hi, c in zip(cube_min, cube_max, center)]
    return sum(_octant(px, py, pz, r)
               for px in dists[0] for py in dists[1] for pz in dists[2])


def approximate_covered_volume(cube_min: numpy.ndarray, cube_max: numpy.ndarray, cube_vol, sphere_vol,
                               points: numpy.ndarray, r):
    """Estimate covered cube volume for one or more points.

    The cube is approximated by a sphere with the same center and a radius
    equal to half its space diagonal.  The sphere-volume/cube-volume ratio is
    attenuated by the distance from the node to the cube center.  This avoids
    numerical integration.  For an ``(N, 3)`` array, one volume is returned
    for each point.
    """
    single_point = points.ndim == 1
    points = points.reshape(-1, 3)

    sides = cube_max - cube_min
    cube_center = (cube_min + cube_max) / 2
    distance = numpy.linalg.norm(points - cube_center, axis=1)
    cell_radius = 0.5 * numpy.linalg.norm(sides)

    sphere_fraction = sphere_vol / cube_vol
    distance_fraction = 1.0 - distance / (r + cell_radius)
    fraction = min(1.0, sphere_fraction) * numpy.maximum(distance_fraction, 0.0) ** 3
    result = cube_vol * numpy.minimum(fraction, 1.0)
    result[distance + cell_radius <= r] = cube_vol
    result[distance >= r + cell_radius] = 0.0
    return result[0] if single_point else result
