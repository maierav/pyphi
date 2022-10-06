#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_new_big_phi.py

import json
from copy import copy

import pytest

import pyphi
from pyphi.examples import EXAMPLES
from pyphi.jsonify import jsonify
from pyphi.new_big_phi import sia
from pyphi.compute.subsystem import ces

@pytest.fixture
def expected_sia():
    cases = {}
    
    for example in [
        "grid3",
        "basic",
        "basic_noisy_selfloop",
        "xor",
        "fig4"
    ]:
        with open(f"test/data/sia/sia_{example}.json") as f:
            cases[example] = json.load(f)
    
    return cases

# Tests
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@pytest.mark.parametrize(
    "example_subsystem", # TODO more parameters
    [
        "grid3",
        "basic",
        "basic_noisy_selfloop",
        "xor",
        "fig4"
    ]
)
def test_sia(example_subsystem, expected_sia):
    example_func = EXAMPLES["subsystem"][example_subsystem]
    actual_sia = sia(example_func(), parallel=False)
    
    # convert SIA object to JSON format
    actual_sia = copy(actual_sia.__dict__)
    del actual_sia["_ties"]
    actual_sia = jsonify(actual_sia)
    
    for key in expected_sia[example_subsystem]:
        if key == "node_labels":
            for attr in expected_sia[example_subsystem]["node_labels"]:
                if attr != "__id__":
                    assert actual_sia[key][attr] == expected_sia[example_subsystem][key][attr]
        else:
            assert actual_sia[key] == expected_sia[example_subsystem][key]

def test_compute_subsystem_ces():
    assert False == True # TODO

def test_relations():
    assert False == True # TODO