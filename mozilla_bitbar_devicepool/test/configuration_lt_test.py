# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

import pytest

from mozilla_bitbar_devicepool.configuration_lt import ConfigurationLt

# Sample configuration data as a raw YAML string (for writing to file)
SAMPLE_FILE_CONFIG_YAML = """
global:
  contract_device_count: 30
projects:
  defaults:
    # not used yet
    # SCRIPT_REPO_COMMIT: master
    TEST_1: blah
  a55-alpha:
    # lt_device_selector: "Galaxy A55 5G-14"
    # swapped for testing
    lt_device_selector: "Galaxy A51-11"
    TASKCLUSTER_CLIENT_ID: project/autophone/gecko-t-lambda-alpha-a55_z
    TC_WORKER_TYPE: gecko-t-lambda-alpha-a55_zz
  a55-perf:
    lt_device_selector: "Galaxy A55 5G-14"
    # swapped for testing
    # lt_device_selector: "Galaxy A51-11"
    TASKCLUSTER_CLIENT_ID: project/autophone/gecko-t-lambda-perf-a55_yy
    TC_WORKER_TYPE: gecko-t-lambda-perf-a55_y
  test-1:
  #     SCRIPT_REPO_COMMIT: future_commit
    lt_device_selector: "Galaxy A51-11"
  #     TASKCLUSTER_CLIENT_ID: project/autophone/gecko-t-lambda-test-1_t
  #     TC_WORKER_TYPE: gecko-t-lambda-gw-test-1_tt
  #     # override SCRIPT_REPO_COMMIT with a test commit
device_groups:
  # this block is not used yet (not possible with LT API), future goal. see lt_device_selector in projects.
  a55-perf:
    R5CX4089QNL
    R5CXC1AHV4M
    R5CXC1ALFED
    R5CXC1AMMNK
    R5CXC1AMNFY
    R5CXC1ANGLT
    R5CXC1AP2KT
    R5CXC1ARCER
    R5CXC1ARELR
    R5CXC1ARM0A
    R5CXC1ASA0L
    R5CXC1ASA2E
    R5CXC1ASA3P
    R5CXC1ASLHH
    R5CXC1HZK0W
    R5CY128X71B
    R5CY21T22NH
    RZCX31FDGJE
    RZCX50TW03H
    RZCX71ZVF6J
    RZCX821GXDJ
    RZCX821GYPX
    RZCXA0H3T9P
    RZCY10LGB6W
    RZCY10Y4HWD
    RZCY10Y4QVX
    RZCY10Y4TAV
    RZCY10Y4TBY
    RZCY10Y4TJX
    RZCY10Y548K
    RZCY2011M7N
    RZCY203N75Z
    RZCY204AAZD
  a55-alpha:
    # the only device with a power meter
    R5CXC1HZKLR
  test-1:
    # a51
    RZ8NB0WJ47H
  test-2:
"""

SAMPLE_FILE_CONFIG_YAML_2 = """
global:
  contract_device_count: 1319
projects:
  defaults:
    # not used yet
    # SCRIPT_REPO_COMMIT: master
    TEST_1: blah
  a55-alpha:
    # lt_device_selector: "Galaxy A55 5G-14"
    # swapped for testing
    lt_device_selector: "Galaxy A51-11"
    TASKCLUSTER_CLIENT_ID: project/autophone/gecko-t-lambda-alpha-a55
    TC_WORKER_TYPE: gecko-t-lambda-alpha-a55
  a55-perf:
    lt_device_selector: "Galaxy A55 5G-14"
    # swapped for testing
    # lt_device_selector: "Galaxy A51-11"
    TASKCLUSTER_CLIENT_ID: project/autophone/gecko-t-lambda-perf-a55
    TC_WORKER_TYPE: gecko-t-lambda-perf-a55
  test-1:
  #     SCRIPT_REPO_COMMIT: future_commit
    lt_device_selector: "Galaxy A51-11"
  #     TASKCLUSTER_CLIENT_ID: project/autophone/gecko-t-lambda-test-1
  #     TC_WORKER_TYPE: gecko-t-lambda-gw-test-1
  #     # override SCRIPT_REPO_COMMIT with a test commit
device_groups:
  # this block is not used yet (not possible with LT API), future goal. see lt_device_selector in projects.
  a55-perf:
    R5CX4089QNL
    R5CXC1AHV4M
    R5CXC1ALFED
  a55-alpha:
    # the only device with a power meter
    R5CXC1HZKLR
  test-1:
    # a51
    RZ8NB0WJ47H
  test-2:
"""


# create a fixture using SAMPLE_FILE_CONFIG_YAML
@pytest.fixture
def sample_file_config(tmp_path):
    """
    Fixture to create a temporary YAML file with sample configuration data.
    """
    # Create a temporary config file
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    config_file.write_text(SAMPLE_FILE_CONFIG_YAML)

    return str(config_file)


@pytest.fixture
def sample_file_config_2(tmp_path):
    """
    Fixture to create a temporary YAML file with sample configuration data.
    """
    # Create a temporary config file
    config_dir = tmp_path / "config2"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    config_file.write_text(SAMPLE_FILE_CONFIG_YAML_2)

    return str(config_file)


# TODO: create a fixture for configured_lt_instance
@pytest.fixture
def configured_lt_instance(sample_file_config):
    """
    Fixture to create a configured instance of ConfigurationLt.
    """
    config_lt = ConfigurationLt(ci_mode=True)
    config_lt.configure(config_path=sample_file_config)
    return config_lt


@pytest.fixture
def configured_lt_instance2(sample_file_config_2):
    """
    Fixture to create a configured instance of ConfigurationLt.
    """
    config_lt = ConfigurationLt(ci_mode=True)
    config_lt.configure(config_path=sample_file_config_2)
    return config_lt


def test_configure(configured_lt_instance):
    """
    Tests that the configure method correctly loads the configuration.
    """
    # test that defaults are set in projects
    assert configured_lt_instance.config["projects"]["a55-alpha"]["TEST_1"] == "blah"

    # test the device group massaging
    #
    # check that it's a list
    assert isinstance(configured_lt_instance.config["device_groups"]["a55-perf"], list)
    # check that the list is not empty
    assert len(configured_lt_instance.config["device_groups"]["a55-perf"]) > 0
    # check that the list contains a few of the expected devices
    assert "R5CX4089QNL" in configured_lt_instance.config["device_groups"]["a55-perf"]
    assert "R5CXC1AHV4M" in configured_lt_instance.config["device_groups"]["a55-perf"]


def test_load_file_config(sample_file_config):
    """
    Tests that _load_file_config correctly loads configuration from an actual file.
    """
    config_lt = ConfigurationLt()

    #
    os.environ["gecko_t_lambda_alpha_a55_zz"] = "fake_client_id"
    os.environ["gecko_t_lambda_perf_a55_y"] = "fake_client_id"
    os.environ["LT_ACCESS_KEY"] = "not_a_real_lt_key"
    os.environ["LT_USERNAME"] = "bro"

    config_lt.configure(config_path=sample_file_config)
    assert len(config_lt.config) > 0


def test_load_file_config_file_not_found(tmp_path):
    """
    Tests that _load_file_config raises FileNotFoundError when the file doesn't exist.
    """
    config_lt = ConfigurationLt()

    # Define a path that does not exist within the temporary directory
    non_existent_path = tmp_path / "non_existent_config.yml"

    # Assert that FileNotFoundError is raised when trying to load a non-existent file
    with pytest.raises(FileNotFoundError):
        config_lt.configure(config_path=str(non_existent_path))


# TODO: test test_get_device_count_for_project
def test_get_device_count_for_project(configured_lt_instance):
    """
    Tests that get_device_count_for_project correctly counts the number of devices for a given project.
    """
    # Test with a project that has devices
    assert configured_lt_instance.get_device_count_for_project("a55-perf") == 33
    assert configured_lt_instance.get_device_count_for_project("a55-alpha") == 1

    # Test with a project that has no devices
    assert configured_lt_instance.get_device_count_for_project("non_existent_project") == 0
    # TODO: have option that makes it raise on invalid project name


# TODO: test test_get_project_for_udid
def test_get_project_for_udid(configured_lt_instance):
    """
    Tests that get_project_for_udid correctly finds the project associated with a given device UDID.
    """
    # Test with a device that exists
    assert configured_lt_instance.get_project_for_udid("R5CX4089QNL") == "a55-perf"
    assert configured_lt_instance.get_project_for_udid("R5CXC1HZKLR") == "a55-alpha"
    assert configured_lt_instance.get_project_for_udid("RZ8NB0WJ47H") == "test-1"

    # Test with a device that does not exist
    assert configured_lt_instance.get_project_for_udid("non_existent_device") is None
    # TODO: have option that makes it raise on invalid device name


def test_get_fully_configured_projects(configured_lt_instance):
    """
    Tests that the fully_configured method correctly identifies if the configuration is complete.
    """
    # Test with a fully configured instance
    assert configured_lt_instance.get_fully_configured_projects() == ["a55-alpha", "a55-perf"]

    # Test with an instance that is not fully configured
    # Create a new instance without configuration
    # incomplete_config_lt = ConfigurationLt()
    # assert incomplete_config_lt.fully_configured() is False


def test_is_project_fully_configured(configured_lt_instance):
    """
    Tests that the is_project_fully_configured method correctly identifies if a specific project is fully configured.
    """
    # Test with a fully configured project
    assert configured_lt_instance.is_project_fully_configured("a55-alpha") is True

    # Test with a partially configured project
    assert configured_lt_instance.is_project_fully_configured("a55-perf") is True

    # Test with a project that is not fully configured
    assert configured_lt_instance.is_project_fully_configured("test-1") is False
    assert configured_lt_instance.is_project_fully_configured("test-2") is False

    # Test with a non-existent project
    assert configured_lt_instance.is_project_fully_configured("non_existent_project") is False


def test_get_total_device_count(configured_lt_instance, configured_lt_instance2):
    """
    Tests that the get_total_device_count method correctly counts the total number of devices across all projects.
    """
    # Test with a fully configured instance
    assert configured_lt_instance.get_total_device_count() == 35


def test_get_total_device_count_2(configured_lt_instance2):
    """
    Tests that the get_total_device_count method correctly counts the total number of devices across all projects.
    """
    # Test with a fully configured instance
    assert configured_lt_instance2.get_total_device_count() == 5


def test_global_contract_device_count(configured_lt_instance2):
    """
    Tests that the global.contract_device_count is correctly set in the configuration.
    """
    assert configured_lt_instance2.global_contract_device_count == 1319
