import numpy as np
import pytest

from pyphi import config, Subsystem, actual, examples, models
from pyphi.constants import Direction


# TODO
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   * test context equality/hash
#   * state_probability


# Fixtures
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@pytest.fixture
def context():
    return examples.ac_ex1_context()


@pytest.fixture
def empty_context(context):
    return actual.Context(context.network, context.before_state,
                          context.after_state, (), ())


# Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def test_context_initialization(context):
    assert context.effect_system.state == (0, 1, 1)
    assert context.cause_system.state == (1, 0, 0)
    assert tuple(n.state for n in context.cause_system.nodes) == (1, 0, 0)


def test_purview_state(context):
    assert context.purview_state(Direction.PAST) == (0, 1, 1)
    assert context.purview_state(Direction.FUTURE) == (1, 0, 0)


def test_mechanism_state(context):
    assert context.mechanism_state(Direction.PAST) == (1, 0, 0)
    assert context.mechanism_state(Direction.FUTURE) == (0, 1, 1)


def test_system_dict(context):
    assert context.system[Direction.PAST] == context.cause_system
    assert context.system[Direction.FUTURE] == context.effect_system


def test_context_len(context, empty_context):
    assert len(context) == 3
    assert len(empty_context) == 0


def test_context_bool(context, empty_context):
    assert bool(context)
    assert not bool(empty_context)


def test_context_apply_cut(context):
    cut = models.ActualCut((1,), (2,), (), (0,))
    cut_context = context.apply_cut(cut)
    assert cut_context.before_state == context.before_state
    assert cut_context.after_state == context.after_state
    assert cut_context.cause_indices == context.cause_indices
    assert cut_context.effect_indices == context.effect_indices
    assert cut_context.cut == cut
    assert cut_context != context


def test_to_json(context):
    context.to_json()

# Test AC models
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def acmip(**kwargs):
    defaults = {
        'alpha': 0.0,
        'state': None,
        'direction': None,
        'mechanism': (),
        'purview': (),
        'partition': None,
        'probability': 0.0,
        'partitioned_probability': 0.0,
    }
    defaults.update(kwargs)
    return models.AcMip(**defaults)


def action(**kwargs):
    return models.Occurence(acmip(**kwargs))


def test_acmip_ordering():
    assert acmip() == acmip()
    assert acmip(alpha=0.0) < acmip(alpha=1.0)
    assert acmip(alpha=0.0, mechanism=(1, 2)) <= acmip(alpha=1.0, mechanism=(1,))
    assert acmip(alpha=0.0, mechanism=(1, 2)) > acmip(alpha=0.0, mechanism=(1,))

    with pytest.raises(TypeError):
        acmip(direction=Direction.PAST) < acmip(direction=Direction.FUTURE)

    with config.override(PICK_SMALLEST_PURVIEW=True):
        assert acmip(purview=(1,)) > acmip(purview=(0, 2))


def test_acmip_hash():
    hash(acmip())


def test_acmip_phi_alias():
    assert acmip(alpha=3.3).phi == 3.3


def test_action_ordering():
    assert action() == action()

    assert action(alpha=0.0) < action(alpha=1.0)
    assert action(alpha=0.0, mechanism=(1, 2)) <= action(alpha=1.0, mechanism=(1,))
    assert action(alpha=0.0, mechanism=(1, 2)) > action(alpha=0.0, mechanism=(1,))

    with pytest.raises(TypeError):
        action(direction=Direction.PAST) < action(direction=Direction.FUTURE)


@pytest.mark.parametrize('direction,mechanism,purview,repertoire', [
    (Direction.PAST, (0,), (1,), [[[0.3333333], [0.66666667]]]),
    (Direction.PAST, (0,), (2,), [[[0.3333333, 0.66666667]]]),
    (Direction.PAST, (0,), (1, 2), [[[0, 0.3333333], [0.3333333, 0.3333333]]]),
    (Direction.PAST, (1,), (1,), [[[.5], [.5]]]),
    (Direction.FUTURE, (1,), (0,), [[[0]], [[1]]]),
    (Direction.FUTURE, (2,), (0,), [[[0]], [[1]]]),
    (Direction.FUTURE, (1, 2), (0,), [[[0]], [[1]]]),
    (Direction.FUTURE, (0,), (1,), [[[0.5], [0.5]]])
])
def test_repertoires(direction, mechanism, purview, repertoire, context):
    np.testing.assert_array_almost_equal(
        context._repertoire(direction, mechanism, purview),
        repertoire)


@pytest.mark.parametrize('direction,mechanism,purview,probability', [
    (Direction.PAST, (0,), (1,), 0.66666667),
    (Direction.PAST, (0,), (2,), 0.66666667),
    (Direction.PAST, (0,), (1, 2), 0.3333333),
    (Direction.PAST, (1,), (1,), 0.5),
    (Direction.FUTURE, (1,), (0,), 1),
    (Direction.FUTURE, (2,), (0,), 1),
    (Direction.FUTURE, (1, 2), (0,), 1),
    (Direction.FUTURE, (0,), (1,), 0.5)
])
def test_probability(direction, mechanism, purview, probability, context):
    assert np.isclose(context.probability(direction, mechanism, purview),
                      probability)


def test_unconstrained_probability(context):
    assert context.unconstrained_probability(Direction.PAST, (1,)) == 0.5
    assert context.unconstrained_probability(Direction.FUTURE, (0,)) == 0.75


@pytest.mark.parametrize('mechanism,purview,ratio', [
    ((0,), (1,), 0.41504),
    ((0,), (2,), 0.41504),
    ((0,), (1,2), 0.41504),
    ((1,), (1,), 0)
])
def test_cause_ratio(mechanism, purview, ratio, context):
    assert np.isclose(context.cause_ratio(mechanism, purview), ratio)


@pytest.mark.parametrize('mechanism,purview,ratio', [
    ((1,), (0,), 0.41504),
    ((2,), (0,), 0.41504),
    ((1, 2), (0,), 0.41504),
    ((0,), (1,), 0)
])
def test_effect_ratio(mechanism, purview, ratio, context):
    assert np.isclose(context.effect_ratio(mechanism, purview), ratio)


def test_ac_ex1_context(context):
    '''Basic regression test for ac_ex1 example.'''

    cause_account = actual.directed_account(context, Direction.PAST)
    assert len(cause_account) == 1
    cmip = cause_account[0].mip

    assert cmip.mechanism == (0,)
    assert cmip.purview == (1,)
    assert cmip.direction == Direction.PAST
    assert cmip.state == (1, 0, 0)
    assert cmip.alpha == 0.41503749927884376
    assert cmip.probability == 0.66666666666666663
    assert cmip.partitioned_probability == 0.5
    assert cmip.partition == (((), (1,)), ((0,), ()))

    effect_account = actual.directed_account(context, Direction.FUTURE)
    assert len(effect_account) == 2
    emip0 = effect_account[0].mip
    emip1 = effect_account[1].mip

    assert emip0.mechanism == (1,)
    assert emip0.purview == (0,)
    assert emip0.direction == Direction.FUTURE
    assert emip0.state == (0, 1, 1)
    assert emip0.alpha == 0.41503749927884376
    assert emip0.probability == 1.0
    assert emip0.partitioned_probability == 0.75
    assert emip0.partition == (((), (0,)), ((1,), ()))

    assert emip1.mechanism == (2,)
    assert emip1.purview == (0,)
    assert emip1.direction == Direction.FUTURE
    assert emip1.state == (0, 1, 1)
    assert emip1.alpha == 0.41503749927884376
    assert emip1.probability == 1.0
    assert emip1.partitioned_probability == 0.75
    assert emip1.partition == (((), (0,)), ((2,), ()))


# TODO: fix unreachable state issue
@pytest.mark.xfail
def test_ac_ex3_context():
    '''Regression test for ac_ex3 example'''
    context = examples.ac_ex3_context()

    cause_account = actual.directed_account(context, Direction.PAST)
    assert len(cause_account) == 1
    cmip = cause_account[0].mip

    assert cmip.mechanism == (0,)
    assert cmip.purview == (2,)
    assert cmip.direction == Direction.PAST
    assert cmip.state == (0, 0, 0)
    assert cmip.alpha == 0.33333333333333326
    assert cmip.probability == 0.66666666666666663
    assert cmip.partitioned_probability == 0.5
    assert cmip.partition == (((), (2,)), ((0,), ()))

    effect_account = actual.directed_account(context, Direction.FUTURE)
    assert len(effect_account) == 2
    emip0 = effect_account[0].mip
    emip1 = effect_account[1].mip

    assert emip0.mechanism == (1,)
    assert emip0.purview == (0,)
    assert emip0.direction == Direction.FUTURE
    assert emip0.state == (0, 0, 1)
    assert emip0.alpha == 0.33333333333333331
    assert emip0.probability == 1.0
    assert emip0.partitioned_probability == 0.75
    assert emip0.partition == (((), (0,)), ((1,), ()))

    assert emip1.mechanism == (2,)
    assert emip1.purview == (0,)
    assert emip1.direction == Direction.FUTURE
    assert emip1.state == (0, 0, 1)
    assert emip1.alpha == 0.33333333333333331
    assert emip1.probability == 1.0
    assert emip1.partitioned_probability == 0.75
    assert emip1.partition == (((), (0,)), ((2,), ()))


def test_actual_cut_indices():
    cut = models.ActualCut((0,), (4,), (2,), (5,))
    assert cut.indices == (0, 2, 4, 5)
    cut = models.ActualCut((0, 2), (), (0, 2), ())
    assert cut.indices == (0, 2)


def test_actual_apply_cut():
    cut = models.ActualCut((0, 2), (), (0,), (2,))
    cm = np.ones((3, 3))
    assert np.array_equal(cut.apply_cut(cm), np.array([
        [1, 1, 0],
        [1, 1, 1],
        [1, 1, 0]]))


def test_actual_cut_matrix():
    cut = models.ActualCut((0, 2), (), (0,), (2,))
    assert np.array_equal(cut.cut_matrix(3), np.array([
        [0, 0, 1],
        [0, 0, 0],
        [0, 0, 1]]))


def test_big_acmip(context):
    bigmip = actual.big_acmip(context)
    assert bigmip.alpha == 0.4150374992788438
    assert bigmip.cut == models.ActualCut((1,), (2,), (), (0,))
    assert len(bigmip.unpartitioned_account) == 3
    assert len(bigmip.partitioned_account) == 2


def test_null_ac_bigmip(context):
    bigmip = actual._null_ac_bigmip(context, Direction.PAST)
    assert bigmip.context == context
    assert bigmip.direction == Direction.PAST
    assert bigmip.unpartitioned_account == ()
    assert bigmip.partitioned_account == ()
    assert bigmip.alpha == 0.0

    bigmip = actual._null_ac_bigmip(context, Direction.PAST, alpha=float('inf'))
    assert bigmip.alpha == float('inf')


def test_causal_nexus(standard):
    nexus = actual.causal_nexus(standard, (0, 0, 1), (1, 1, 0))
    assert nexus.alpha == 2.0
    assert nexus.direction == Direction.BIDIRECTIONAL
    assert nexus.context.cause_indices == (0, 1)
    assert nexus.context.effect_indices == (2,)


def test_true_events(standard):
    states = ((1, 0, 0), (0, 0, 1), (1, 1, 0))  # Past, current, future
    events = actual.true_events(standard, *states)

    assert len(events) == 2

    true_cause1, true_effect1 = events[0]
    assert events[0].mechanism == (0,)

    assert true_cause1.alpha == 1.0
    assert true_cause1.mechanism == (0,)
    assert true_cause1.purview == (2,)
    assert true_cause1.direction == Direction.PAST

    assert true_effect1.alpha == 1.0
    assert true_effect1.mechanism == (0,)
    assert true_effect1.purview == (2,)
    assert true_effect1.direction == Direction.FUTURE

    true_cause2, true_effect2 = events[1]
    assert events[1].mechanism == (2,)

    assert true_cause2.alpha == 1.0
    assert true_cause2.mechanism == (2,)
    assert true_cause2.purview == (0,)
    assert true_cause2.direction == Direction.PAST

    assert true_effect2.alpha == 1.0
    assert true_effect2.mechanism == (2,)
    assert true_effect2.purview == (0,)
    assert true_effect2.direction == Direction.FUTURE


def test_true_constellation(standard):
    past_state = (1, 0, 0)
    current_state = (0, 0, 1)
    future_state = (1, 1, 0)
    subsystem = Subsystem(standard, current_state, standard.node_indices)

    constellation = actual.true_constellation(subsystem, past_state, future_state)

    assert len(constellation) == 2
    actual_cause, actual_effect = constellation

    assert actual_cause.purview == (0, 1)
    assert actual_cause.mechanism == (2,)

    assert actual_effect.purview == (1,)
    assert actual_effect.mechanism == (2,)


def test_extrinsic_events(standard):
    states = ((1, 0, 0), (0, 0, 1), (1, 1, 0))  # Past, current, future

    events = actual.extrinsic_events(standard, *states)

    assert len(events) == 1

    true_cause, true_effect = events[0]
    assert events[0].mechanism == (2,)

    assert true_cause.alpha == 1.0
    assert true_cause.mechanism == (2,)
    assert true_cause.purview == (0, 1)
    assert true_cause.direction == Direction.PAST

    assert true_effect.alpha == 1.0
    assert true_effect.mechanism == (2,)
    assert true_effect.purview == (1,)
    assert true_effect.direction == Direction.FUTURE


@pytest.fixture
def ac_net():
    return examples.actual_causation()


def test_actual_causation_example(ac_net):
    assert np.array_equal(ac_net.cm, np.array([
        [0, 0, 1, 1],
        [0, 0, 1, 1],
        [0, 0, 0, 0],
        [0, 0, 0, 0]]))
    assert np.array_equal(ac_net.tpm, [
        [[[[ 0.5,  0.5,  0. ,  0. ],
           [ 0.5,  0.5,  0. ,  0. ]],
          [[ 0.5,  0.5,  0. ,  0. ],
           [ 0.5,  0.5,  0. ,  0. ]]],
         [[[ 0.5,  0.5,  1. ,  0. ],
           [ 0.5,  0.5,  1. ,  0. ]],
          [[ 0.5,  0.5,  1. ,  0. ],
           [ 0.5,  0.5,  1. ,  0. ]]]],
        [[[[ 0.5,  0.5,  1. ,  0. ],
           [ 0.5,  0.5,  1. ,  0. ]],
          [[ 0.5,  0.5,  1. ,  0. ],
           [ 0.5,  0.5,  1. ,  0. ]]],
         [[[ 0.5,  0.5,  1. ,  1. ],
           [ 0.5,  0.5,  1. ,  1. ]],
          [[ 0.5,  0.5,  1. ,  1. ],
           [ 0.5,  0.5,  1. ,  1. ]]]]])
