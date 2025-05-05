# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

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
    },
}


def test_get_project_for_udid():
    """
    Tests that get_project_for_udid correctly identifies the project for a given UDID.
    """
    config_lt = ConfigurationLt(ci_mode=True)
    # Manually set the config instead of loading from file
    config_lt.config = SAMPLE_CONFIG.copy()  # Use a copy to avoid modifying the original dict
    # Manually set required env vars for expansion (or mock if preferred)
    config_lt.config["projects"]["projectA"]["TASKCLUSTER_ACCESS_TOKEN"] = "fake_token_A"
    config_lt.config["projects"]["projectB"]["TASKCLUSTER_ACCESS_TOKEN"] = "fake_token_B"

    config_lt.expand_configuration()  # Process device_groups

    assert config_lt.get_project_for_udid("udid1") == "projectA"
    assert config_lt.get_project_for_udid("udid2") == "projectA"
    assert config_lt.get_project_for_udid("udid3") == "projectB"
    assert config_lt.get_project_for_udid("udid4") == "projectB"
    assert config_lt.get_project_for_udid("unknown_udid") is None
    # Test case sensitivity (assuming UDIDs are case-sensitive)
    assert config_lt.get_project_for_udid("UDID1") is None
