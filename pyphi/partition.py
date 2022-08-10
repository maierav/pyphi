#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# partition.py

"""
Functions for generating partitions.
"""

import functools
import itertools
from itertools import chain, permutations, product

import numpy as np

from . import config
from .cache import cache
from .combinatorics import pairs
from .conf import fallback
from .direction import Direction
from .models.cuts import (
    Bipartition,
    CompleteGeneralKCut,
    Cut,
    GeneralKCut,
    KPartition,
    Part,
    RelationPart,
    RelationPartition,
    SystemPartition,
    Tripartition,
)
from .registry import Registry


# TODO move purely combinatorial functions to `combinatorics`
# From stackoverflow.com/questions/19368375/set-partitions-in-python
def _partitions(collection):
    """Generate all set partitions of a collection.

    Example:
        >>> list(partitions(range(3)))  # doctest: +NORMALIZE_WHITESPACE
        [[[0, 1, 2]],
         [[0], [1, 2]],
         [[0, 1], [2]],
         [[1], [0, 2]],
         [[0], [1], [2]]]
    """
    collection = list(collection)

    # Special cases
    if not collection:
        return

    if len(collection) == 1:
        yield [collection]
        return

    first = collection[0]
    for smaller in partitions(collection[1:]):
        for n, subset in enumerate(smaller):
            yield smaller[:n] + [[first] + subset] + smaller[n + 1 :]
        yield [[first]] + smaller


@functools.wraps(_partitions)
def partitions(collection, nontrivial=False):
    if nontrivial:
        return itertools.islice(_partitions(collection), 1, None)
    return _partitions(collection)


@cache(cache={}, maxmem=None)
def bipartition_indices(N):
    """Return indices for undirected bipartitions of a sequence.

    Args:
        N (int): The length of the sequence.

    Returns:
        list: A list of tuples containing the indices for each of the two
        parts.

    Example:
        >>> N = 3
        >>> bipartition_indices(N)
        [((), (0, 1, 2)), ((0,), (1, 2)), ((1,), (0, 2)), ((0, 1), (2,))]
    """
    result = []
    if N <= 0:
        return result

    for i in range(2 ** (N - 1)):
        part = [[], []]
        for n in range(N):
            bit = (i >> n) & 1
            part[bit].append(n)
        result.append((tuple(part[1]), tuple(part[0])))
    return result


# TODO? rename to `bipartitions`
def bipartition(seq, nontrivial=False):
    """Return a list of bipartitions for a sequence.

    Args:
        a (Iterable): The sequence to partition.

    Returns:
        list[tuple[tuple]]: A list of tuples containing each of the two
        partitions.

    Example:
        >>> bipartition((1,2,3))
        [((), (1, 2, 3)), ((1,), (2, 3)), ((2,), (1, 3)), ((1, 2), (3,))]
    """
    bipartitions = [
        (tuple(seq[i] for i in part0_idx), tuple(seq[j] for j in part1_idx))
        for part0_idx, part1_idx in bipartition_indices(len(seq))
    ]
    if nontrivial:
        return bipartitions[1:]
    return bipartitions


@cache(cache={}, maxmem=None)
def directed_bipartition_indices(N):
    """Return indices for directed bipartitions of a sequence.

    Args:
        N (int): The length of the sequence.

    Returns:
        list: A list of tuples containing the indices for each of the two
        parts.

    Example:
        >>> N = 3
        >>> directed_bipartition_indices(N)  # doctest: +NORMALIZE_WHITESPACE
        [((), (0, 1, 2)),
         ((0,), (1, 2)),
         ((1,), (0, 2)),
         ((0, 1), (2,)),
         ((2,), (0, 1)),
         ((0, 2), (1,)),
         ((1, 2), (0,)),
         ((0, 1, 2), ())]
    """
    indices = bipartition_indices(N)
    return indices + [idx[::-1] for idx in indices[::-1]]


# TODO? [optimization] optimize this to use indices rather than nodes
def directed_bipartition(seq, nontrivial=False):
    """Return a list of directed bipartitions for a sequence.

    Args:
        seq (Iterable): The sequence to partition.

    Returns:
        list[tuple[tuple]]: A list of tuples containing each of the two
        parts.

    Example:
        >>> directed_bipartition((1, 2, 3))  # doctest: +NORMALIZE_WHITESPACE
        [((), (1, 2, 3)),
         ((1,), (2, 3)),
         ((2,), (1, 3)),
         ((1, 2), (3,)),
         ((3,), (1, 2)),
         ((1, 3), (2,)),
         ((2, 3), (1,)),
         ((1, 2, 3), ())]
    """
    bipartitions = [
        (tuple(seq[i] for i in part0_idx), tuple(seq[j] for j in part1_idx))
        for part0_idx, part1_idx in directed_bipartition_indices(len(seq))
    ]
    if nontrivial:
        # The first and last partitions have a part that is empty; skip them.
        # NOTE: This depends on the implementation of
        # `directed_partition_indices`.
        return bipartitions[1:-1]
    return bipartitions


def bipartition_of_one(seq):
    """Generate bipartitions where one part is of length 1."""
    seq = list(seq)
    for i, elt in enumerate(seq):
        yield ((elt,), tuple(seq[:i] + seq[(i + 1) :]))


def reverse_elements(seq):
    """Reverse the elements of a sequence."""
    for elt in seq:
        yield elt[::-1]


def directed_bipartition_of_one(seq):
    """Generate directed bipartitions where one part is of length 1.

    Args:
        seq (Iterable): The sequence to partition.

    Returns:
        list[tuple[tuple]]: A list of tuples containing each of the two
        partitions.

    Example:
        >>> partitions = directed_bipartition_of_one((1, 2, 3))
        >>> list(partitions)  # doctest: +NORMALIZE_WHITESPACE
        [((1,), (2, 3)),
         ((2,), (1, 3)),
         ((3,), (1, 2)),
         ((2, 3), (1,)),
         ((1, 3), (2,)),
         ((1, 2), (3,))]
    """
    bipartitions = list(bipartition_of_one(seq))
    return chain(bipartitions, reverse_elements(bipartitions))


@cache(cache={}, maxmem=None)
def directed_tripartition_indices(N):
    """Return indices for directed tripartitions of a sequence.

    Args:
        N (int): The length of the sequence.

    Returns:
        list[tuple]: A list of tuples containing the indices for each
        partition.

    Example:
        >>> N = 1
        >>> directed_tripartition_indices(N)
        [((0,), (), ()), ((), (0,), ()), ((), (), (0,))]
    """
    result = []
    if N <= 0:
        return result

    base = [0, 1, 2]
    for key in product(base, repeat=N):
        part = [[], [], []]
        for i, location in enumerate(key):
            part[location].append(i)

        result.append(tuple(tuple(p) for p in part))

    return result


def directed_tripartition(seq):
    """Generator over all directed tripartitions of a sequence.

    Args:
        seq (Iterable): a sequence.

    Yields:
        tuple[tuple]: A tripartition of ``seq``.

    Example:
        >>> seq = (2, 5)
        >>> list(directed_tripartition(seq))  # doctest: +NORMALIZE_WHITESPACE
        [((2, 5), (), ()),
         ((2,), (5,), ()),
         ((2,), (), (5,)),
         ((5,), (2,), ()),
         ((), (2, 5), ()),
         ((), (2,), (5,)),
         ((5,), (), (2,)),
         ((), (5,), (2,)),
         ((), (), (2, 5))]
    """
    for a, b, c in directed_tripartition_indices(len(seq)):
        yield (
            tuple(seq[i] for i in a),
            tuple(seq[j] for j in b),
            tuple(seq[k] for k in c),
        )


# Knuth's algorithm for k-partitions of a set
# codereview.stackexchange.com/questions/1526/finding-all-k-subset-partitions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def _visit(n, a, k, collection):
    # pylint: disable=missing-docstring
    ps = [[] for i in range(k)]
    for j in range(n):
        ps[a[j + 1]].append(collection[j])
    return ps


def _f(mu, nu, sigma, n, a, k, collection):
    # flake8: noqa
    # pylint: disable=missing-docstring
    if mu == 2:
        yield _visit(n, a, k, collection)
    else:
        for v in _f(mu - 1, nu - 1, (mu + sigma) % 2, n, a, k, collection):
            yield v
    if nu == mu + 1:
        a[mu] = mu - 1
        yield _visit(n, a, k, collection)
        while a[nu] > 0:
            a[nu] = a[nu] - 1
            yield _visit(n, a, k, collection)
    elif nu > mu + 1:
        if (mu + sigma) % 2 == 1:
            a[nu - 1] = mu - 1
        else:
            a[mu] = mu - 1
        if (a[nu] + sigma) % 2 == 1:
            for v in _b(mu, nu - 1, 0, n, a, k, collection):
                yield v
        else:
            for v in _f(mu, nu - 1, 0, n, a, k, collection):
                yield v
        while a[nu] > 0:
            a[nu] = a[nu] - 1
            if (a[nu] + sigma) % 2 == 1:
                for v in _b(mu, nu - 1, 0, n, a, k, collection):
                    yield v
            else:
                for v in _f(mu, nu - 1, 0, n, a, k, collection):
                    yield v


def _b(mu, nu, sigma, n, a, k, collection):
    # flake8: noqa
    # pylint: disable=missing-docstring
    if nu == mu + 1:
        while a[nu] < mu - 1:
            yield _visit(n, a, k, collection)
            a[nu] = a[nu] + 1
        yield _visit(n, a, k, collection)
        a[mu] = 0
    elif nu > mu + 1:
        if (a[nu] + sigma) % 2 == 1:
            for v in _f(mu, nu - 1, 0, n, a, k, collection):
                yield v
        else:
            for v in _b(mu, nu - 1, 0, n, a, k, collection):
                yield v
        while a[nu] < mu - 1:
            a[nu] = a[nu] + 1
            if (a[nu] + sigma) % 2 == 1:
                for v in _f(mu, nu - 1, 0, n, a, k, collection):
                    yield v
            else:
                for v in _b(mu, nu - 1, 0, n, a, k, collection):
                    yield v
        if (mu + sigma) % 2 == 1:
            a[nu - 1] = 0
        else:
            a[mu] = 0
    if mu == 2:
        yield _visit(n, a, k, collection)
    else:
        for v in _b(mu - 1, nu - 1, (mu + sigma) % 2, n, a, k, collection):
            yield v


def k_partitions(collection, k):
    """Generate all ``k``-partitions of a collection.

    Example:
        >>> list(k_partitions(range(3), 2))
        [[[0, 1], [2]], [[0], [1, 2]], [[0, 2], [1]]]
    """
    collection = list(collection)
    n = len(collection)

    # Special cases
    if n == 0 or k < 1:
        return []
    if k == 1:
        return [[collection]]
    if k == n:
        return [[[item] for item in collection]]

    a = [0] * (n + 1)
    for j in range(1, k + 1):
        a[n - k + j] = j - 1
    return _f(k, n, 0, n, a, k, collection)


# Concrete partitions producing PyPhi models
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Distinction partitions
# ~~~~~~~~~~~~~~~~~~~~~~


class PartitionRegistry(Registry):
    """Storage for partition schemes registered with PyPhi.

    Users can define custom partitions:

    Examples:
        >>> @partition_types.register('NONE')  # doctest: +SKIP
        ... def no_partitions(mechanism, purview):
        ...    return []

    And use them by setting ``config.PARTITION_TYPE = 'NONE'``
    """

    desc = "distinction partitions"


partition_types = PartitionRegistry()


def mip_partitions(mechanism, purview, node_labels=None):
    """Return a generator over all mechanism-purview partitions, based on the
    current configuration.
    """
    func = partition_types[config.PARTITION_TYPE]
    return func(mechanism, purview, node_labels)


@partition_types.register("BI")
def mip_bipartitions(mechanism, purview, node_labels=None):
    r"""Return an generator of all |small_phi| bipartitions of a mechanism over
    a purview.

    Excludes all bipartitions where one half is entirely empty, *e.g*::

         A     ∅
        ─── ✕ ───
         B     ∅

    is not valid, but ::

         A     ∅
        ─── ✕ ───
         ∅     B

    is.

    Args:
        mechanism (tuple[int]): The mechanism to partition
        purview (tuple[int]): The purview to partition

    Yields:
        Bipartition: Where each bipartition is::

            bipart[0].mechanism   bipart[1].mechanism
            ─────────────────── ✕ ───────────────────
            bipart[0].purview     bipart[1].purview

    Example:
        >>> mechanism = (0,)
        >>> purview = (2, 3)
        >>> for partition in mip_bipartitions(mechanism, purview):
        ...     print(partition, '\n')  # doctest: +NORMALIZE_WHITESPACE
         ∅     0
        ─── ✕ ───
         2     3
        <BLANKLINE>
         ∅     0
        ─── ✕ ───
         3     2
        <BLANKLINE>
         ∅     0
        ─── ✕ ───
        2,3    ∅
    """
    numerators = bipartition(mechanism)
    denominators = directed_bipartition(purview)

    for n, d in product(numerators, denominators):
        if (n[0] or d[0]) and (n[1] or d[1]):
            yield Bipartition(
                Part(n[0], d[0], node_labels=node_labels),
                Part(n[1], d[1], node_labels=node_labels),
                node_labels=node_labels,
            )


@partition_types.register("TRI")
def wedge_partitions(mechanism, purview, node_labels=None):
    """Return an iterator over all wedge partitions.

    These are partitions which strictly split the mechanism and allow a subset
    of the purview to be split into a third partition, e.g.::

         A     B     ∅
        ─── ✕ ─── ✕ ───
         B     C     D

    See |PARTITION_TYPE| in |config| for more information.

    Args:
        mechanism (tuple[int]): A mechanism.
        purview (tuple[int]): A purview.

    Yields:
        Tripartition: all unique tripartitions of this mechanism and purview.
    """
    numerators = bipartition(mechanism)
    denominators = directed_tripartition(purview)

    yielded = set()

    def valid(factoring):
        """Return whether the factoring should be considered."""
        # pylint: disable=too-many-boolean-expressions
        numerator, denominator = factoring
        return (
            (numerator[0] or denominator[0])
            and (numerator[1] or denominator[1])
            and (
                (numerator[0] and numerator[1])
                or not denominator[0]
                or not denominator[1]
            )
        )

    for n, d in filter(valid, product(numerators, denominators)):
        # Normalize order of parts to remove duplicates.
        tripart = Tripartition(
            Part(n[0], d[0], node_labels=node_labels),
            Part(n[1], d[1], node_labels=node_labels),
            Part((), d[2], node_labels=node_labels),
            node_labels=node_labels,
        ).normalize()

        def nonempty(part):
            """Check that the part is not empty."""
            return part.mechanism or part.purview

        def compressible(tripart):
            """Check if the tripartition can be transformed into a causally
            equivalent partition by combing two of its parts; e.g., A/∅ × B/∅ ×
            ∅/CD is equivalent to AB/∅ × ∅/CD so we don't include it.
            """
            pairs = [
                (tripart[0], tripart[1]),
                (tripart[0], tripart[2]),
                (tripart[1], tripart[2]),
            ]
            for x, y in pairs:
                if (
                    nonempty(x)
                    and nonempty(y)
                    and (x.mechanism + y.mechanism == () or x.purview + y.purview == ())
                ):
                    return True
            return False

        if not compressible(tripart) and tripart not in yielded:
            yielded.add(tripart)
            yield tripart


@partition_types.register("ALL")
def all_partitions(mechanism, purview, node_labels=None):
    """Return all possible partitions of a mechanism and purview.

    Partitions can consist of any number of parts.

    Args:
        mechanism (tuple[int]): A mechanism.
        purview (tuple[int]): A purview.

    Yields:
        KPartition: A partition of this mechanism and purview into ``k`` parts.
    """
    for mechanism_partition in partitions(mechanism):
        mechanism_partition.append([])
        n_mechanism_parts = len(mechanism_partition)
        max_purview_partition = min(len(purview), n_mechanism_parts)
        for n_purview_parts in range(1, max_purview_partition + 1):
            n_empty = n_mechanism_parts - n_purview_parts
            for purview_partition in k_partitions(purview, n_purview_parts):
                purview_partition = [tuple(_list) for _list in purview_partition]
                # Extend with empty tuples so purview partition has same size
                # as mechanism purview
                purview_partition.extend([()] * n_empty)

                # Unique permutations to avoid duplicates empties
                for purview_permutation in set(permutations(purview_partition)):

                    parts = [
                        Part(tuple(m), tuple(p), node_labels=node_labels)
                        for m, p in zip(mechanism_partition, purview_permutation)
                    ]

                    # Must partition the mechanism, unless the purview is fully
                    # cut away from the mechanism.
                    if parts[0].mechanism == mechanism and parts[0].purview:
                        continue

                    yield KPartition(*parts, node_labels=node_labels)


class CompletePartition(KPartition):
    """Represents the partition that completely separates mechanism and purview."""

    pass


def complete_partition(mechanism, purview):
    n_parts = len(next(mip_partitions(mechanism, purview)))
    parts = [Part((), ())] * (n_parts - 2) + [Part((), purview), Part(mechanism, ())]
    return CompletePartition(*parts)


class AtomicPartition(KPartition):
    """Represents the partition that separates all inter-element connections."""

    pass


def atomic_partition(elements):
    return AtomicPartition(*[Part((elt,), (elt,)) for elt in elements])


# Relation partitions
# ~~~~~~~~~~~~~~~~~~~

relation_partition_types = PartitionRegistry()


@relation_partition_types.register("TRI")
def relation_tripartitions(relata, candidate_joint_purview, node_labels=None):
    overlap_partitions = wedge_partitions(
        tuple(range(len(relata))), candidate_joint_purview
    )
    return (
        RelationPartition(
            relata,
            *(
                RelationPart(
                    mechanism=part.mechanism,
                    purview=part.purview,
                    relata=relata,
                    node_labels=node_labels,
                )
                for part in partition
            ),
            node_labels=node_labels,
        )
        for partition in overlap_partitions
    )


def relation_partition_one_distinction(
    relata, candidate_joint_purview, i, node_labels=None
):
    relata_indices = tuple(range(len(relata)))
    mechanism_parts = [(i,), relata_indices[:i] + relata_indices[(i + 1) :]]
    purview_parts = [(), candidate_joint_purview]
    return RelationPartition(
        relata,
        *(
            RelationPart(
                mechanism=mechanism,
                purview=purview,
                relata=relata,
                node_labels=node_labels,
            )
            for mechanism, purview in zip(mechanism_parts, purview_parts)
        ),
        node_labels=node_labels,
    )


@relation_partition_types.register("BI_CUT_ONE")
def relation_bipartitions_of_one(relata, candidate_joint_purview, node_labels=None):
    for i in range(len(relata)):
        yield relation_partition_one_distinction(
            relata, candidate_joint_purview, i, node_labels=node_labels
        )


class AggregationRegistry(Registry):
    """Storage for relation partition aggregation schemes registered with PyPhi.

    Users can define custom aggregations:

    Examples:
        >>> @relation_partition_aggregations.register('ZEROS')  # doctest: +SKIP
        ... def all_zeros(specified):
        ...    return np.zeros(specified.shape[1:])

    And use them by setting ``config.RELATION_PARTITION_AGGREGATION = 'NONE'``
    """

    desc = "partition aggregations"


relation_partition_aggregations = AggregationRegistry()


summation = relation_partition_aggregations.register("SUM")(np.sum)
minimum = relation_partition_aggregations.register("MIN")(np.min)


# System partitions
# ~~~~~~~~~~~~~~~~~


class SystemPartitionRegistry(Registry):
    """Storage for system partition schemes registered with PyPhi.

    Users can define custom partitions:

    Examples:
        >>> @system_partition_types.register('NONE')  # doctest: +SKIP
        ... def no_partitions(mechanism, purview):
        ...    return []

    And use them by setting ``config.SYSTEM_PARTITION_TYPE = 'NONE'``
    """

    desc = "system partitions"


system_partition_types = SystemPartitionRegistry()


# TODO(4.0) consolidate Cut and SystemPartition logic


def _bipartitions_to_cuts(func):
    """Decorator to return equivalent Cut objects from a set of bipartitions."""

    @functools.wraps(func)
    def wrapper(*args, node_labels=None, **kwargs):
        bipartitions = func(*args, **kwargs)
        return [
            Cut(bipartition[0], bipartition[1], node_labels=node_labels)
            for bipartition in bipartitions
        ]

    return wrapper


@system_partition_types.register("DIRECTED_BI")
@_bipartitions_to_cuts
def system_directed_bipartitions(nodes):
    # Don't consider trivial partitions where one part is empty
    return directed_bipartition(nodes, nontrivial=True)


@system_partition_types.register("DIRECTED_BI_CUT_ONE")
@_bipartitions_to_cuts
def system_directed_bipartitions_cut_one(nodes):
    return directed_bipartition_of_one(nodes)


@system_partition_types.register("DIRECTED_BI_SIMPLE")
def system_bipartitions_simple(nodes, node_labels=None):
    # Use a list instead of generator for progress bar totals since it's linear
    # in the size of the system
    partitions = []
    for n in range(1, len(nodes)):
        part1, part2 = nodes[:n], nodes[n:]
        partitions.append(
            Cut(from_nodes=part1, to_nodes=part2, node_labels=node_labels)
        )
        partitions.append(
            Cut(from_nodes=part2, to_nodes=part1, node_labels=node_labels)
        )
    return partitions


def _bipartitions_to_temporal_system_partitions(func):
    """Decorator to return temporally-directed SystemPartition objects from a
    set of bipartitions.
    """

    @functools.wraps(func)
    def wrapper(*args, node_labels=None, **kwargs):
        for bipartition in func(*args, **kwargs):
            for direction in Direction.both():
                yield SystemPartition(
                    direction,
                    bipartition[0],
                    bipartition[1],
                    node_labels=node_labels,
                )

    return wrapper


@system_partition_types.register("TEMPORAL_DIRECTED_BI")
@_bipartitions_to_temporal_system_partitions
def system_temporal_directed_bipartitions(nodes):
    # Don't consider trivial partitions where one part is empty
    return directed_bipartition(nodes, nontrivial=True)


@system_partition_types.register("TEMPORAL_DIRECTED_BI_CUT_ONE")
@_bipartitions_to_temporal_system_partitions
def system_temporal_directed_bipartitions_cut_one(nodes):
    return directed_bipartition_of_one(nodes)


def _cut_matrices(n):
    # Skip first all-zero combination since they are all zeros
    repeat = n ** 2 - n
    mid = repeat // 2
    for combination in itertools.islice(product([0, 1], repeat=repeat), 1, None):
        cm = np.empty([n, n], dtype=int)
        cm[np.diag_indices(n)] = 0
        cm[np.triu_indices(n, k=1)] = combination[:mid]
        cm[np.tril_indices(n, k=-1)] = combination[mid:]
        yield cm


@system_partition_types.register("GENERAL")
def general(node_indices, node_labels=None):
    yield CompleteGeneralKCut(node_indices, node_labels=node_labels)
    for cut_matrix in _cut_matrices(len(node_indices)):
        yield GeneralKCut(node_indices, cut_matrix, node_labels=node_labels)


def system_partitions(nodes, node_labels=None, partition_scheme=None, filter_func=None):
    """Return the currently configured system partitions for the given nodes."""
    partition_scheme = fallback(partition_scheme, config.SYSTEM_PARTITION_TYPE)
    partitions = system_partition_types[partition_scheme](
        nodes, node_labels=node_labels
    )
    if filter_func is not None:
        return filter(filter_func, partitions)
    return partitions
