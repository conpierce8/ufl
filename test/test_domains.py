
"""Tests of domain language and attaching domains to forms."""

import pytest
from mockobjects import MockMesh

import ufl  # noqa: F401
from ufl import (Cell, Coefficient, Constant, FunctionSpace, Mesh, ds, dS, dx, hexahedron, interval, quadrilateral,
                 tetrahedron, triangle)
from ufl.algorithms import compute_form_data
from ufl.finiteelement import FiniteElement
from ufl.pullback import IdentityPullback  # noqa: F401
from ufl.pullback import identity_pullback
from ufl.sobolevspace import H1

all_cells = (interval, triangle, tetrahedron, quadrilateral, hexahedron)


def test_construct_domains_from_cells():
    for cell in all_cells:
        d = cell.geometric_dimension()
        Mesh(FiniteElement("Lagrange", cell, 1, (d, ), identity_pullback, H1))


def test_construct_domains_with_names():
    for cell in all_cells:
        d = cell.geometric_dimension()
        e = FiniteElement("Lagrange", cell, 1, (d, ), identity_pullback, H1)
        D2 = Mesh(e, ufl_id=2)
        D3 = Mesh(e, ufl_id=3)
        D3b = Mesh(e, ufl_id=3)
        assert D2 != D3
        assert D3 == D3b


def test_domains_sort_by_name():
    # This ordering is rather arbitrary, but at least this shows sorting is
    # working
    domains1 = [Mesh(FiniteElement("Lagrange", cell, 1, (cell.geometric_dimension(), ),
                                   identity_pullback, H1),
                     ufl_id=hash(cell.cellname()))
                for cell in all_cells]
    domains2 = [Mesh(FiniteElement("Lagrange", cell, 1, (cell.geometric_dimension(), ),
                                   identity_pullback, H1),
                     ufl_id=hash(cell.cellname()))
                for cell in sorted(all_cells)]
    sdomains = sorted(domains1, key=lambda D: (D.geometric_dimension(),
                                               D.topological_dimension(),
                                               D.ufl_cell(),
                                               D.ufl_id()))
    assert sdomains != domains1
    assert sdomains == domains2


def test_topdomain_creation():
    D = Mesh(FiniteElement("Lagrange", interval, 1, (1, ), identity_pullback, H1))
    assert D.geometric_dimension() == 1
    D = Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1))
    assert D.geometric_dimension() == 2
    D = Mesh(FiniteElement("Lagrange", tetrahedron, 1, (3, ), identity_pullback, H1))
    assert D.geometric_dimension() == 3


def test_cell_legacy_case():
    # Passing cell like old code does
    D = Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1))

    V = FiniteElement("Lagrange", triangle, 1, (), identity_pullback, H1)
    f = Coefficient(FunctionSpace(D, V))
    assert f.ufl_domains() == (D, )

    M = f * dx
    assert M.ufl_domains() == (D, )


def test_simple_domain_case():
    # Creating domain from just cell with label like new dolfin will do
    D = Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=3)

    V = FunctionSpace(D, FiniteElement("Lagrange", D.ufl_cell(), 1, (), identity_pullback, "H1"))
    f = Coefficient(V)
    assert f.ufl_domains() == (D, )

    M = f * dx
    assert M.ufl_domains() == (D, )


def test_creating_domains_with_coordinate_fields():  # FIXME: Rewrite for new approach
    # Definition of higher order domain, element, coefficient, form

    # Mesh with P2 representation of coordinates
    cell = triangle
    P2 = FiniteElement("Lagrange", cell, 2, (2, ), identity_pullback, H1)
    domain = Mesh(P2)

    # Piecewise linear function space over quadratic mesh
    element = FiniteElement("Lagrange", cell, 1, (), identity_pullback, H1)
    V = FunctionSpace(domain, element)

    f = Coefficient(V)
    M = f * dx
    assert f.ufl_domains() == (domain, )
    assert M.ufl_domains() == (domain, )

    # Test the gymnastics that dolfin will have to go through
    domain2 = Mesh(P2, ufl_id=domain.ufl_id())
    V2 = FunctionSpace(domain2, eval(repr(V.ufl_element())))
    f2 = Coefficient(V2, count=f.count())
    assert f == f2
    assert domain == domain2
    assert V == V2


def test_join_domains():
    from ufl.domain import join_domains
    mesh7 = MockMesh(7)
    mesh8 = MockMesh(8)
    triangle3 = Cell("triangle", geometric_dimension=3)
    xa = FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1)
    xb = FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1)

    # Equal domains are joined
    assert 1 == len(join_domains([
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7),
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7)]))
    assert 1 == len(join_domains([
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7, cargo=mesh7),
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7, cargo=mesh7)]))
    assert 1 == len(join_domains([Mesh(xa, ufl_id=3), Mesh(xa, ufl_id=3)]))

    # Different domains are not joined
    assert 2 == len(join_domains([
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1)),
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1))]))
    assert 2 == len(join_domains([
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7),
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=8)]))
    assert 2 == len(join_domains([
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7),
        Mesh(FiniteElement("Lagrange", quadrilateral, 1, (2, ), identity_pullback, H1), ufl_id=8)]))
    assert 2 == len(join_domains([Mesh(xa, ufl_id=7), Mesh(xa, ufl_id=8)]))
    assert 2 == len(join_domains([Mesh(xa), Mesh(xb)]))

    # Incompatible coordinates require labeling
    xc = Coefficient(FunctionSpace(
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1)),
        FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1)))
    xd = Coefficient(FunctionSpace(
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1)),
        FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1)))
    with pytest.raises(BaseException):
        join_domains([Mesh(xc), Mesh(xd)])

    # Incompatible data is checked if and only if the domains are the same
    assert 2 == len(join_domains([
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7, cargo=mesh7),
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=8, cargo=mesh8)]))
    assert 2 == len(join_domains([
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7, cargo=mesh7),
        Mesh(FiniteElement("Lagrange", quadrilateral, 1, (2, ), identity_pullback, H1),
             ufl_id=8, cargo=mesh8)]))
    # Geometric dimensions must match
    with pytest.raises(BaseException):
        join_domains([
            Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1)),
            Mesh(FiniteElement("Lagrange", triangle3, 1, (3, ), identity_pullback, H1))])
    with pytest.raises(BaseException):
        join_domains([
            Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7, cargo=mesh7),
            Mesh(FiniteElement("Lagrange", triangle3, 1, (3, ), identity_pullback, H1), ufl_id=8, cargo=mesh8)])
    # Cargo and mesh ids must match
    with pytest.raises(BaseException):
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7, cargo=mesh8)

    # Nones are removed
    assert 2 == len(join_domains([
        None, Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=3),
        None, Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=3),
        None, Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=4)]))
    assert 2 == len(join_domains([
        Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1), ufl_id=7), None,
        Mesh(FiniteElement("Lagrange", quadrilateral, 1, (2, ), identity_pullback, H1), ufl_id=8)]))
    assert None not in join_domains([
        Mesh(FiniteElement("Lagrange", triangle3, 1, (3, ), identity_pullback, H1), ufl_id=7), None,
        Mesh(FiniteElement("Lagrange", tetrahedron, 1, (3, ), identity_pullback, H1), ufl_id=8)])


def test_everywhere_integrals_with_backwards_compatibility():
    D = Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1))

    V = FunctionSpace(D, FiniteElement("Lagrange", triangle, 1, (), identity_pullback, H1))
    f = Coefficient(V)

    a = f * dx
    ida, = compute_form_data(a).integral_data

    # Check some integral data
    assert ida.integral_type == "cell"
    assert len(ida.subdomain_id) == 1
    assert ida.subdomain_id[0] == "otherwise"
    assert ida.metadata == {}

    # Integrands are not equal because of renumbering
    itg1 = ida.integrals[0].integrand()
    itg2 = a.integrals()[0].integrand()
    assert type(itg1) is type(itg2)
    assert itg1.ufl_element() == itg2.ufl_element()


def test_merge_sort_integral_data():
    D = Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1))

    V = FunctionSpace(D, FiniteElement("CG", triangle, 1, (), identity_pullback, H1))

    u = Coefficient(V)
    c = Constant(D)
    a = c * dS((2, 4)) + u * dx + u * ds + 2 * u * dx(3) + 2 * c * dS + 2 * u * dx((1, 4))
    form_data = compute_form_data(a, do_append_everywhere_integrals=False).integral_data
    assert len(form_data) == 5

    # Check some integral data
    assert form_data[0].integral_type == "cell"
    assert len(form_data[0].subdomain_id) == 1
    assert form_data[0].subdomain_id[0] == "otherwise"
    assert form_data[0].metadata == {}

    assert form_data[1].integral_type == "cell"
    assert len(form_data[1].subdomain_id) == 3
    assert form_data[1].subdomain_id[0] == 1
    assert form_data[1].subdomain_id[1] == 3
    assert form_data[1].subdomain_id[2] == 4
    assert form_data[1].metadata == {}

    assert form_data[2].integral_type == "exterior_facet"
    assert len(form_data[2].subdomain_id) == 1
    assert form_data[2].subdomain_id[0] == "otherwise"
    assert form_data[2].metadata == {}

    assert form_data[3].integral_type == "interior_facet"
    assert len(form_data[3].subdomain_id) == 1
    assert form_data[3].subdomain_id[0] == "otherwise"
    assert form_data[3].metadata == {}

    assert form_data[4].integral_type == "interior_facet"
    assert len(form_data[4].subdomain_id) == 2
    assert form_data[4].subdomain_id[0] == 2
    assert form_data[4].subdomain_id[1] == 4
    assert form_data[4].metadata == {}
