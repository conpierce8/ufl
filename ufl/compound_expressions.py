"""Functions implementing compound expressions as equivalent representations using basic operators."""
# Copyright (C) 2008-2016 Martin Sandve Alnæs and Anders Logg
#
# This file is part of UFL (https://www.fenicsproject.org)
#
# SPDX-License-Identifier:    LGPL-3.0-or-later
#
# Modified by Anders Logg, 2009-2010

import warnings

from ufl.constantvalue import Zero, zero
from ufl.core.multiindex import Index, indices
from ufl.operators import sqrt
from ufl.tensors import as_matrix, as_tensor, as_vector

# Note: To avoid typing errors, the expressions for cofactor and
# deviatoric parts below were created with the script
# tensoralgebrastrings.py under sandbox/scripts/

# Note: Avoiding or delaying application of these horrible expressions
# would be a major improvement to UFL and the form compiler toolchain.
# It could easily be a moderate to major undertaking to get rid of
# though.


def cross_expr(a, b):
    """Symbolic cross product."""
    assert len(a) == 3
    assert len(b) == 3

    def c(i, j):
        return a[i] * b[j] - a[j] * b[i]
    return as_vector((c(1, 2), c(2, 0), c(0, 1)))


def generic_pseudo_determinant_expr(A):
    """Compute the pseudo-determinant of A: sqrt(det(A.T*A))."""
    i, j, k = indices(3)
    ATA = as_tensor(A[k, i] * A[k, j], (i, j))
    return sqrt(determinant_expr(ATA))


def pseudo_determinant_expr(A):
    """Compute the pseudo-determinant of A."""
    m, n = A.ufl_shape
    if n == 1:
        # Special case 1xm for simpler expression
        i = Index()
        return sqrt(A[i, 0] * A[i, 0])
    elif n == 2 and m == 3:
        # Special case 2x3 for simpler expression
        c = cross_expr(A[:, 0], A[:, 1])
        i = Index()
        return sqrt(c[i] * c[i])
    else:
        # Generic formulation based on A.T*A
        return generic_pseudo_determinant_expr(A)


def generic_pseudo_inverse_expr(A):
    """Compute the Penrose-Moore pseudo-inverse of A: (A.T*A)^-1 * A.T."""
    i, j, k = indices(3)
    ATA = as_tensor(A[k, i] * A[k, j], (i, j))
    ATAinv = inverse_expr(ATA)
    q, r, s = indices(3)
    return as_tensor(ATAinv[r, q] * A[s, q], (r, s))


def pseudo_inverse_expr(A):
    """Compute the Penrose-Moore pseudo-inverse of A: (A.T*A)^-1 * A.T."""
    m, n = A.ufl_shape
    if n == 1:
        # Simpler special case for 1d
        i, j, k = indices(3)
        return as_tensor(A[i, j], (j, i)) / (A[k, 0] * A[k, 0])
    else:
        # Generic formulation
        return generic_pseudo_inverse_expr(A)


def determinant_expr(A):
    """Compute the (pseudo-)determinant of A."""
    sh = A.ufl_shape
    if isinstance(A, Zero):
        return zero()
    elif sh == ():
        return A
    elif sh[0] == sh[1]:
        if sh[0] == 1:
            return A[0, 0]
        elif sh[0] == 2:
            return determinant_expr_2x2(A)
        elif sh[0] == 3:
            return determinant_expr_3x3(A)
        else:
            return determinant_expr_nxn(A)
    else:
        return pseudo_determinant_expr(A)

    # TODO: Implement generally for all dimensions?
    raise ValueError(f"determinant_expr not implemented for shape {sh}.")


def _det_2x2(B, i, j, k, l):  # noqa: E741
    """Determinant of a 2 by 2 matrix."""
    return B[i, k] * B[j, l] - B[i, l] * B[j, k]


def determinant_expr_2x2(B):
    """Determinant of a 2 by 2 matrix."""
    return _det_2x2(B, 0, 1, 0, 1)


def old_determinant_expr_3x3(A):
    """Determinant of a 3 by 3 matrix."""
    warnings.warn("The use of old_determinant_expr_3x3 is deprecated and will be removed after December 2023. "
                  "Please, use determinant_expr_3x3 instead", FutureWarning)
    return A[0, 0] * _det_2x2(A, 1, 2, 1, 2) + A[0, 1] * _det_2x2(A, 1, 2, 2, 0) + A[0, 2] * _det_2x2(A, 1, 2, 0, 1)


def determinant_expr_3x3(A):
    """Determinant of a 3 by 3 matrix."""
    return codeterminant_expr_nxn(A, [0, 1, 2], [0, 1, 2])


def determinant_expr_nxn(A):
    """Determinant of a n by n matrix."""
    nrow, ncol = A.ufl_shape
    assert nrow == ncol
    return codeterminant_expr_nxn(A, list(range(nrow)), list(range(ncol)))


def codeterminant_expr_nxn(A, rows, cols):
    """Determinant of a n by n matrix."""
    if len(rows) == 2:
        return _det_2x2(A, rows[0], rows[1], cols[0], cols[1])
    codet = 0.0
    r = rows[0]
    subrows = rows[1:]
    for i, c in enumerate(cols):
        subcols = cols[:i] + cols[i + 1:]
        codet += (-1)**i * A[r, c] * codeterminant_expr_nxn(A, subrows, subcols)
    return codet


def inverse_expr(A):
    """Compute the inverse of A."""
    sh = A.ufl_shape
    if sh == ():
        return 1.0 / A
    elif sh[0] == sh[1]:
        if sh[0] == 1:
            return as_tensor(((1.0 / A[0, 0],),))
        else:
            return adj_expr(A) / determinant_expr(A)
    else:
        return pseudo_inverse_expr(A)


def adj_expr(A):
    """Adjoint of a matrix."""
    sh = A.ufl_shape
    if sh[0] != sh[1]:
        raise ValueError("Expecting square matrix.")

    if sh[0] == 2:
        return adj_expr_2x2(A)
    elif sh[0] == 3:
        return adj_expr_3x3(A)
    elif sh[0] == 4:
        return adj_expr_4x4(A)

    raise ValueError(f"adj_expr not implemented for dimension {sh[0]}.")


def adj_expr_2x2(A):
    """Adjoint of a 2 by 2 matrix."""
    return as_matrix([[A[1, 1], -A[0, 1]],
                      [-A[1, 0], A[0, 0]]])


def adj_expr_3x3(A):
    """Adjoint of a 3 by 3 matrix."""
    return as_matrix([[
        A[2, 2] * A[1, 1] - A[1, 2] * A[2, 1],
        -A[0, 1] * A[2, 2] + A[0, 2] * A[2, 1],
        A[0, 1] * A[1, 2] - A[0, 2] * A[1, 1],
    ], [
        -A[2, 2] * A[1, 0] + A[1, 2] * A[2, 0],
        -A[0, 2] * A[2, 0] + A[2, 2] * A[0, 0],
        A[0, 2] * A[1, 0] - A[1, 2] * A[0, 0],
    ], [
        A[1, 0] * A[2, 1] - A[2, 0] * A[1, 1],
        A[0, 1] * A[2, 0] - A[0, 0] * A[2, 1],
        A[0, 0] * A[1, 1] - A[0, 1] * A[1, 0],
    ]])


def adj_expr_4x4(A):
    """Adjoint of a 4 by 4 matrix."""
    return as_matrix([[
        -A[3, 3] * A[2, 1] * A[1, 2] + A[1, 2] * A[3, 1] * A[2, 3] + A[1, 1] * A[3, 3] * A[2, 2] - A[3, 1] * A[2, 2] * A[1, 3] + A[2, 1] * A[1, 3] * A[3, 2] - A[1, 1] * A[3, 2] * A[2, 3],  # noqa: E501
        -A[3, 1] * A[0, 2] * A[2, 3] + A[0, 1] * A[3, 2] * A[2, 3] - A[0, 3] * A[2, 1] * A[3, 2] + A[3, 3] * A[2, 1] * A[0, 2] - A[3, 3] * A[0, 1] * A[2, 2] + A[0, 3] * A[3, 1] * A[2, 2],  # noqa: E501
        A[3, 1] * A[1, 3] * A[0, 2] + A[1, 1] * A[0, 3] * A[3, 2] - A[0, 3] * A[1, 2] * A[3, 1] - A[0, 1] * A[1, 3] * A[3, 2] + A[3, 3] * A[1, 2] * A[0, 1] - A[1, 1] * A[3, 3] * A[0, 2],  # noqa: E501
        A[1, 1] * A[0, 2] * A[2, 3] - A[2, 1] * A[1, 3] * A[0, 2] + A[0, 3] * A[2, 1] * A[1, 2] - A[1, 2] * A[0, 1] * A[2, 3] - A[1, 1] * A[0, 3] * A[2, 2] + A[0, 1] * A[2, 2] * A[1, 3],  # noqa: E501
    ], [
        A[3, 3] * A[1, 2] * A[2, 0] - A[3, 0] * A[1, 2] * A[2, 3] + A[1, 0] * A[3, 2] * A[2, 3] - A[3, 3] * A[1, 0] * A[2, 2] - A[1, 3] * A[3, 2] * A[2, 0] + A[3, 0] * A[2, 2] * A[1, 3],  # noqa: E501
        A[0, 3] * A[3, 2] * A[2, 0] - A[0, 3] * A[3, 0] * A[2, 2] + A[3, 3] * A[0, 0] * A[2, 2] + A[3, 0] * A[0, 2] * A[2, 3] - A[0, 0] * A[3, 2] * A[2, 3] - A[3, 3] * A[0, 2] * A[2, 0],  # noqa: E501
        -A[3, 3] * A[0, 0] * A[1, 2] + A[0, 0] * A[1, 3] * A[3, 2] - A[3, 0] * A[1, 3] * A[0, 2] + A[3, 3] * A[1, 0] * A[0, 2] + A[0, 3] * A[3, 0] * A[1, 2] - A[0, 3] * A[1, 0] * A[3, 2],  # noqa: E501
        A[0, 3] * A[1, 0] * A[2, 2] + A[1, 3] * A[0, 2] * A[2, 0] - A[0, 0] * A[2, 2] * A[1, 3] - A[0, 3] * A[1, 2] * A[2, 0] + A[0, 0] * A[1, 2] * A[2, 3] - A[1, 0] * A[0, 2] * A[2, 3],  # noqa: E501
    ], [
        A[3, 1] * A[1, 3] * A[2, 0] + A[3, 3] * A[2, 1] * A[1, 0] + A[1, 1] * A[3, 0] * A[2, 3] - A[1, 0] * A[3, 1] * A[2, 3] - A[3, 0] * A[2, 1] * A[1, 3] - A[1, 1] * A[3, 3] * A[2, 0],  # noqa: E501
        A[3, 3] * A[0, 1] * A[2, 0] - A[3, 3] * A[0, 0] * A[2, 1] - A[0, 3] * A[3, 1] * A[2, 0] - A[3, 0] * A[0, 1] * A[2, 3] + A[0, 0] * A[3, 1] * A[2, 3] + A[0, 3] * A[3, 0] * A[2, 1],  # noqa: E501
        -A[0, 0] * A[3, 1] * A[1, 3] + A[0, 3] * A[1, 0] * A[3, 1] - A[3, 3] * A[1, 0] * A[0, 1] + A[1, 1] * A[3, 3] * A[0, 0] - A[1, 1] * A[0, 3] * A[3, 0] + A[3, 0] * A[0, 1] * A[1, 3],  # noqa: E501
        A[0, 0] * A[2, 1] * A[1, 3] + A[1, 0] * A[0, 1] * A[2, 3] - A[0, 3] * A[2, 1] * A[1, 0] + A[1, 1] * A[0, 3] * A[2, 0] - A[1, 1] * A[0, 0] * A[2, 3] - A[0, 1] * A[1, 3] * A[2, 0],  # noqa: E501
    ], [
        -A[1, 2] * A[3, 1] * A[2, 0] - A[2, 1] * A[1, 0] * A[3, 2] + A[3, 0] * A[2, 1] * A[1, 2] - A[1, 1] * A[3, 0] * A[2, 2] + A[1, 0] * A[3, 1] * A[2, 2] + A[1, 1] * A[3, 2] * A[2, 0],  # noqa: E501
        -A[3, 0] * A[2, 1] * A[0, 2] - A[0, 1] * A[3, 2] * A[2, 0] + A[3, 1] * A[0, 2] * A[2, 0] - A[0, 0] * A[3, 1] * A[2, 2] + A[3, 0] * A[0, 1] * A[2, 2] + A[0, 0] * A[2, 1] * A[3, 2],  # noqa: E501
        A[0, 0] * A[1, 2] * A[3, 1] - A[1, 0] * A[3, 1] * A[0, 2] + A[1, 1] * A[3, 0] * A[0, 2] + A[1, 0] * A[0, 1] * A[3, 2] - A[3, 0] * A[1, 2] * A[0, 1] - A[1, 1] * A[0, 0] * A[3, 2],  # noqa: E501
        -A[1, 1] * A[0, 2] * A[2, 0] + A[2, 1] * A[1, 0] * A[0, 2] + A[1, 2] * A[0, 1] * A[2, 0] + A[1, 1] * A[0, 0] * A[2, 2] - A[1, 0] * A[0, 1] * A[2, 2] - A[0, 0] * A[2, 1] * A[1, 2],  # noqa: E501
    ]])


def cofactor_expr(A):
    """Cofactor of a matrix."""
    sh = A.ufl_shape
    if sh[0] != sh[1]:
        raise ValueError("Expecting square matrix.")

    if sh[0] == 2:
        return cofactor_expr_2x2(A)
    elif sh[0] == 3:
        return cofactor_expr_3x3(A)
    elif sh[0] == 4:
        return cofactor_expr_4x4(A)

    raise ValueError(f"cofactor_expr not implemented for dimension {sh[0]}.")


def cofactor_expr_2x2(A):
    """Cofactor of a 2 by 2 matrix."""
    return as_matrix([[A[1, 1], -A[1, 0]],
                      [-A[0, 1], A[0, 0]]])


def cofactor_expr_3x3(A):
    """Cofactor of a 3 by 3 matrix."""
    return as_matrix([[
        A[1, 1] * A[2, 2] - A[2, 1] * A[1, 2],
        A[2, 0] * A[1, 2] - A[1, 0] * A[2, 2],
        -A[2, 0] * A[1, 1] + A[1, 0] * A[2, 1],
    ], [
        A[2, 1] * A[0, 2] - A[0, 1] * A[2, 2],
        A[0, 0] * A[2, 2] - A[2, 0] * A[0, 2],
        -A[0, 0] * A[2, 1] + A[2, 0] * A[0, 1],
    ], [
        A[0, 1] * A[1, 2] - A[1, 1] * A[0, 2],
        A[1, 0] * A[0, 2] - A[0, 0] * A[1, 2],
        -A[1, 0] * A[0, 1] + A[0, 0] * A[1, 1],
    ]])


def cofactor_expr_4x4(A):
    """Cofactor of a 4 by 4 matrix."""
    return as_matrix([[
        -A[3, 1] * A[2, 2] * A[1, 3] - A[3, 2] * A[2, 3] * A[1, 1] + A[1, 3] * A[3, 2] * A[2, 1] + A[3, 1] * A[2, 3] * A[1, 2] + A[2, 2] * A[1, 1] * A[3, 3] - A[3, 3] * A[2, 1] * A[1, 2],  # noqa: E501
        -A[1, 0] * A[2, 2] * A[3, 3] + A[2, 0] * A[3, 3] * A[1, 2] + A[2, 2] * A[1, 3] * A[3, 0] - A[2, 3] * A[3, 0] * A[1, 2] + A[1, 0] * A[3, 2] * A[2, 3] - A[1, 3] * A[3, 2] * A[2, 0],  # noqa: E501
        A[1, 0] * A[3, 3] * A[2, 1] + A[2, 3] * A[1, 1] * A[3, 0] - A[2, 0] * A[1, 1] * A[3, 3] - A[1, 3] * A[3, 0] * A[2, 1] - A[1, 0] * A[3, 1] * A[2, 3] + A[3, 1] * A[1, 3] * A[2, 0],  # noqa: E501
        A[3, 0] * A[2, 1] * A[1, 2] + A[1, 0] * A[3, 1] * A[2, 2] + A[3, 2] * A[2, 0] * A[1, 1] - A[2, 2] * A[1, 1] * A[3, 0] - A[3, 1] * A[2, 0] * A[1, 2] - A[1, 0] * A[3, 2] * A[2, 1],  # noqa: E501
    ], [
        A[3, 1] * A[2, 2] * A[0, 3] + A[0, 2] * A[3, 3] * A[2, 1] + A[0, 1] * A[3, 2] * A[2, 3] - A[3, 1] * A[0, 2] * A[2, 3] - A[0, 1] * A[2, 2] * A[3, 3] - A[3, 2] * A[0, 3] * A[2, 1],  # noqa: E501
        -A[2, 2] * A[0, 3] * A[3, 0] - A[0, 2] * A[2, 0] * A[3, 3] - A[3, 2] * A[2, 3] * A[0, 0] + A[2, 2] * A[3, 3] * A[0, 0] + A[0, 2] * A[2, 3] * A[3, 0] + A[3, 2] * A[2, 0] * A[0, 3],  # noqa: E501
        A[3, 1] * A[2, 3] * A[0, 0] - A[0, 1] * A[2, 3] * A[3, 0] - A[3, 1] * A[2, 0] * A[0, 3] - A[3, 3] * A[0, 0] * A[2, 1] + A[0, 3] * A[3, 0] * A[2, 1] + A[0, 1] * A[2, 0] * A[3, 3],  # noqa: E501
        A[3, 2] * A[0, 0] * A[2, 1] - A[0, 2] * A[3, 0] * A[2, 1] + A[0, 1] * A[2, 2] * A[3, 0] + A[3, 1] * A[0, 2] * A[2, 0] - A[0, 1] * A[3, 2] * A[2, 0] - A[3, 1] * A[2, 2] * A[0, 0],  # noqa: E501
    ], [
        A[3, 1] * A[1, 3] * A[0, 2] - A[0, 2] * A[1, 1] * A[3, 3] - A[3, 1] * A[0, 3] * A[1, 2] + A[3, 2] * A[1, 1] * A[0, 3] + A[0, 1] * A[3, 3] * A[1, 2] - A[0, 1] * A[1, 3] * A[3, 2],  # noqa: E501
        A[1, 3] * A[3, 2] * A[0, 0] - A[1, 0] * A[3, 2] * A[0, 3] - A[1, 3] * A[0, 2] * A[3, 0] + A[0, 3] * A[3, 0] * A[1, 2] + A[1, 0] * A[0, 2] * A[3, 3] - A[3, 3] * A[0, 0] * A[1, 2],  # noqa: E501
        -A[1, 0] * A[0, 1] * A[3, 3] + A[0, 1] * A[1, 3] * A[3, 0] - A[3, 1] * A[1, 3] * A[0, 0] - A[1, 1] * A[0, 3] * A[3, 0] + A[1, 0] * A[3, 1] * A[0, 3] + A[1, 1] * A[3, 3] * A[0, 0],  # noqa: E501
        A[0, 2] * A[1, 1] * A[3, 0] - A[3, 2] * A[1, 1] * A[0, 0] - A[0, 1] * A[3, 0] * A[1, 2] - A[1, 0] * A[3, 1] * A[0, 2] + A[3, 1] * A[0, 0] * A[1, 2] + A[1, 0] * A[0, 1] * A[3, 2],  # noqa: E501
    ], [
        A[0, 3] * A[2, 1] * A[1, 2] + A[0, 2] * A[2, 3] * A[1, 1] + A[0, 1] * A[2, 2] * A[1, 3] - A[2, 2] * A[1, 1] * A[0, 3] - A[1, 3] * A[0, 2] * A[2, 1] - A[0, 1] * A[2, 3] * A[1, 2],  # noqa: E501
        A[1, 0] * A[2, 2] * A[0, 3] + A[1, 3] * A[0, 2] * A[2, 0] - A[1, 0] * A[0, 2] * A[2, 3] - A[2, 0] * A[0, 3] * A[1, 2] - A[2, 2] * A[1, 3] * A[0, 0] + A[2, 3] * A[0, 0] * A[1, 2],  # noqa: E501
        -A[0, 1] * A[1, 3] * A[2, 0] + A[2, 0] * A[1, 1] * A[0, 3] + A[1, 3] * A[0, 0] * A[2, 1] - A[1, 0] * A[0, 3] * A[2, 1] + A[1, 0] * A[0, 1] * A[2, 3] - A[2, 3] * A[1, 1] * A[0, 0],  # noqa: E501
        A[1, 0] * A[0, 2] * A[2, 1] - A[0, 2] * A[2, 0] * A[1, 1] + A[0, 1] * A[2, 0] * A[1, 2] + A[2, 2] * A[1, 1] * A[0, 0] - A[1, 0] * A[0, 1] * A[2, 2] - A[0, 0] * A[2, 1] * A[1, 2],  # noqa: E501
    ]])


def deviatoric_expr(A):
    """Deviatoric of a matrix."""
    sh = A.ufl_shape
    if sh[0] != sh[1]:
        raise ValueError("Expecting square matrix.")

    if sh[0] == 2:
        return deviatoric_expr_2x2(A)
    elif sh[0] == 3:
        return deviatoric_expr_3x3(A)

    raise ValueError(f"deviatoric_expr not implemented for dimension {sh[0]}.")


def deviatoric_expr_2x2(A):
    """Deviatoric of a 2 by 2 matrix."""
    return as_matrix([[-1. / 2 * A[1, 1] + 1. / 2 * A[0, 0], A[0, 1]],
                      [A[1, 0], 1. / 2 * A[1, 1] - 1. / 2 * A[0, 0]]])


def deviatoric_expr_3x3(A):
    """Deviatoric of a 3 by 3 matrix."""
    return as_matrix([[-1. / 3 * A[1, 1] - 1. / 3 * A[2, 2] + 2. / 3 * A[0, 0], A[0, 1], A[0, 2]],
                      [A[1, 0], 2. / 3 * A[1, 1] - 1. / 3 * A[2, 2] - 1. / 3 * A[0, 0], A[1, 2]],
                      [A[2, 0], A[2, 1], -1. / 3 * A[1, 1] + 2. / 3 * A[2, 2] - 1. / 3 * A[0, 0]]])
