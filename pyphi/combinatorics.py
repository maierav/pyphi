#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# combinatorics.py

"""Combinatorial functions."""

from collections import defaultdict
from itertools import chain

import networkx as nx
import numpy as np
from graphillion import setset
from itertools import product

from .cache import cache

# TODO(4.0) move relevant functions from utils here

# TODO(docs) finish documenting
def pair_indices(n, m=None, k=0):
    """Return indices of unordered pairs."""
    if m is None:
        m = n
    n, m = sorted([n, m])
    for i in range(n):
        for j in range(i + k, m):
            yield i, j


# TODO(docs) finish documenting
def pairs(seq, k=0):
    """Return unordered pairs of elements from a sequence.

    NOTE: This is *not* the Cartesian product.
    """
    for i, j in pair_indices(len(seq), k=k):
        yield seq[i], seq[j]


def combinations_with_nonempty_intersection_by_order(sets, min_size=0, max_size=None):
    """Return combinations of sets that have nonempty intersection.

    The returned combinations are sets of the indices of the sets in that
    combination, not the sets themselves.

    Arguments:
        sets (Sequence[frozenset]): The sets to consider. Note that they must be
            ``frozensets``.

    Keyword Arguments:
        min_size (int): The minimum size of the combinations to return. Defaults
            to 0.
        max_size (int): The maximum size of the combinations to return. Defaults
            to ``None``, indicating all sizes.

    Returns:
        defaultdict(set): A mapping from combination size to combinations.
    """
    n = len(sets)
    if max_size is None:
        max_size = n
    min_size = max(2, min_size)

    # Begin by finding pairs with nonempty intersection
    pairs = list(map(frozenset, pair_indices(n, k=1)))
    # Store intersections so successive intersections can be computed faster
    intersections = {
        pair: frozenset.intersection(*[sets[i] for i in pair]) for pair in pairs
    }
    combinations = defaultdict(
        set, {2: set(pair for pair in pairs if intersections[pair])}
    )

    # Iteratively find larger combinations of sets with nonempty intersection
    for k in range(2, max_size):
        nonempty_intersection = combinations[k]
        if nonempty_intersection:
            for i in range(n):
                covered = set()
                for combination in nonempty_intersection:
                    if i in combination:
                        covered.add(combination)
                    else:
                        intersection = sets[i] & intersections[combination]
                        if intersection:
                            new_combination = frozenset([i]) | combination
                            intersections[new_combination] = intersection
                            combinations[k + 1].add(new_combination)
                nonempty_intersection = nonempty_intersection - covered
                if not nonempty_intersection:
                    break
        else:
            break

    return {
        size: combs
        for size, combs in combinations.items()
        if (size >= min_size) and combs
    }


def combinations_with_nonempty_intersection(sets, min_size=0, max_size=None):
    """Return combinations of sets that have nonempty intersection.

    Arguments:
        sets (Sequence[frozenset]): The sets to consider. Note that they must be
            ``frozensets``.

    Keyword Arguments:
        min_size (int): The minimum size of the combinations to return. Defaults
            to 0.
        max_size (int): The maximum size of the combinations to return. Defaults
            to ``None``, indicating all sizes.

    Returns:
        list[frozenset]: The combinations.
    """
    implicit = combinations_with_nonempty_intersection_by_order(
        sets, min_size=min_size, max_size=max_size
    )
    return chain.from_iterable(implicit.values())


def powerset_family(X, min_size=1, max_size=None, universe=None):
    """Return the power set of X as a set family.

    NOTE: The universe is assumed to have been set already.
    """
    if universe is None:
        universe = set(setset.universe())

    # This is necessary since `.set_size(0)` doesn't seem to work
    if min_size > 0:
        negation = [[]]
    else:
        negation = []
    P = ~setset(negation)

    for e in universe - set(X):
        P -= P.join(setset([[e]]))

    exclude = list(range(1, min_size))
    if max_size is not None:
        exclude += list(range(max_size + 1, 2 ** len(X) + 1))
    for k in exclude:
        P -= P.set_size(k)

    return P


def union_powerset_family(sets, min_size=1, max_size=None):
    """Return union of the power set of each set in ``sets``.

    NOTE: The universe must already have been set to (at least) the union of the
    ``sets``.
    """
    U = set(setset.universe())
    S = setset([])
    for s in sets:
        S |= powerset_family(s, min_size=min_size, max_size=max_size, universe=U)
    return S


def maximal_independent_sets(graph):
    """Yield the maximal independent sets of the graph.

    Time complexity is exponential in the worst case.
    """
    # Maximal independent sets are cliques in the graph's complement
    return nx.find_cliques(nx.complement(graph))


@cache(cache={}, maxmem=None)
def num_subsets_larger_than_one_element(n):
    """Return the number of subsets on N elements with size >1.

    |X| = |P(n)| - |{S ∈ P(n) | |S| = 1}| - |{S ∈ P(n) | |S| = 0}|
        = 2^n    - (n choose 1)             - |{ø}|
        = 2^n    - n                        - 1
    """
    return 2 ** n - n - 1


def sum_of_minimum_among_subsets(values):
    """Return sum of the minimum of all subsets with size >1 of some values."""
    # This series counts, from i = 0 to (len(values) - 1), the number of subsets
    # of values of size >1 such that value i is included in all subsets.
    # Since each value is fixed to be in all subsets, this formula differs from
    # `num_subsets_larger_than_one_element`.
    counts = 2 ** (np.arange(len(values), 0, -1) - 1) - 1
    # Sorting ensures that we're taking the minimum of values for each subset
    return np.sum(np.sort(values) * counts)


def sum_of_ratio_of_minimums_among_subsets(num_denum_pairs):
    """Given a list of pairs of numerators and denominators (n_i, d_i) , i=0, ....
    Returns sum of the ratio of minimum numerator to minimum denominator min_i ni / min_i d_i
    over all subsets with size >1.
    Arguments:
        num_denum_pairs (list[tuples(float, float)]): list of pairs of numerators and denominators (n_i, d_i)
    Returns:
        float: Sum of the ratio of minimum numerator to minimum denominator
    """
    # For each possible pair of values, we count the number of
    # times the pair is the minimal pair (sorting makes the counting easier)
    sorted_num_idx = np.argsort([pair[0] for pair in num_denum_pairs])
    sorted_denom_idx = np.argsort([pair[1] for pair in num_denum_pairs])

    sum_ratio = 0
    for i, j in product(range(len(num_denum_pairs)), range(len(num_denum_pairs))):
        # (num, denom) pairs that contain the current candidate values
        candiate_elements = set((sorted_num_idx[i], sorted_denom_idx[j]))
        # the set of elements whose numerator >= this candidate num
        num_superset = set(sorted_num_idx[i:])
        # the set of elements whose denominators >= this candidate denom
        denom_superset = set(sorted_denom_idx[j:])

        superset = num_superset.intersection(denom_superset)
        if not candiate_elements.issubset(superset):
            continue

        # number of subsets of size > 1 of the superset that contain the candiate_elements
        num_occurences = 2 ** len(superset - candiate_elements)
        if len(candiate_elements) == 1:
            num_occurences -= 1

        min_num = num_denum_pairs[sorted_num_idx[i]][0]
        min_denom = num_denum_pairs[sorted_denom_idx[j]][1]
        sum_ratio += num_occurences * min_num / min_denom

    return sum_ratio
