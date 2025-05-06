# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest  # Add pytest import
import copy  # Add copy import
from mozilla_bitbar_devicepool.configuration_lt import ConfigurationLt

# Sample configuration data for testing
SAMPLE_CONFIG = {
    "projects": {
        "defaults": {"some_default": "value"},
        "projectA": {"TC_WORKER_TYPE": "projectA-worker"},
        "projectB": {"TC_WORKER_TYPE": "projectB-worker"},
    },
    "device_groups": {
        "projectA": "udid1 udid2",
        "projectB": "udid3 udid4",
        "projectC": "udid5 udid6 udid7 udid8 udid9 udid10 udid11 udid12 udid13 udid14 udid15 udid16 udid17 udid18 udid19 udid20 udid21 udid22 udid23 udid24 udid25 udid26 udid27 udid28 udid29 udid30",
    },
}


@pytest.fixture
def configured_lt_instance():
    """Fixture to provide a configured ConfigurationLt instance for tests."""
    config_lt = ConfigurationLt(ci_mode=True)
    config_lt.configure(copy.deepcopy(SAMPLE_CONFIG))
    return config_lt


def test_get_project_for_udid(configured_lt_instance):  # Use the fixture
    """
    Tests that get_project_for_udid correctly identifies the project for a given UDID.
    """
    assert configured_lt_instance.get_project_for_udid("udid1") == "projectA"
    assert configured_lt_instance.get_project_for_udid("udid2") == "projectA"
    assert configured_lt_instance.get_project_for_udid("udid3") == "projectB"
    assert configured_lt_instance.get_project_for_udid("udid4") == "projectB"
    assert configured_lt_instance.get_project_for_udid("unknown_udid") is None
    # Test case sensitivity (assuming UDIDs are case-sensitive)
    assert configured_lt_instance.get_project_for_udid("UDID1") is None


def test_get_device_count_for_project(configured_lt_instance):  # Use the fixture
    """
    Tests that get_device_count_for_project correctly counts devices for a given project.
    """
    assert configured_lt_instance.get_device_count_for_project("projectA") == 2
    assert configured_lt_instance.get_device_count_for_project("projectB") == 2
    assert configured_lt_instance.get_device_count_for_project("projectC") == 26
    #
    assert configured_lt_instance.get_device_count_for_project("non_existent_project") == 0
    # being crazy now
    test_str = "udid5 udid6 udid7 udid8 udid9 udid10 udid11 udid12 udid13 udid14 udid15 udid16 udid17 udid18 udid19 udid20 udid21 udid22 udid23 udid24 udid25 udid26 udid27 udid28 udid29 udid30"
    test_str_arr = test_str.split(" ")
    assert configured_lt_instance.get_device_count_for_project("projectC") == len(test_str_arr)
