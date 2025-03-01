# -*- coding: utf-8 -*-
# Copyright (C) 2004-2008 Anders Logg
#
# This file is part of UFL.
#
# UFL is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# UFL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with UFL. If not, see <http://www.gnu.org/licenses/>.
#
# Modified by Martin Sandve Alnæs, 2009
#
# Last changed: 2009-03-02
#
# The bilinear form a(v, u) and linear form L(v) for Poisson's equation.
from ufl import Coefficient, FunctionSpace, Mesh, TestFunction, TrialFunction, dx, grad, inner, triangle
from ufl.finiteelement import FiniteElement
from ufl.pullback import identity_pullback
from ufl.sobolevspace import H1

element = FiniteElement("Lagrange", triangle, 1, (), identity_pullback, H1)
domain = Mesh(FiniteElement("Lagrange", triangle, 1, (2, ), identity_pullback, H1))
space = FunctionSpace(domain, element)

u = TrialFunction(space)
v = TestFunction(space)
f = Coefficient(space)

a = inner(grad(v), grad(u)) * dx(degree=1)
L = v * f * dx(degree=2)
