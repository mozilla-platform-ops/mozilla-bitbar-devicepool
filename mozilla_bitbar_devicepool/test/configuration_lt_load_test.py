# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from mozilla_bitbar_devicepool.configuration_lt import ConfigurationLt

# Sample configuration data as a raw YAML string (for writing to file)
SAMPLE_FILE_CONFIG_YAML = """
global:
  contract_device_count: 30
projects:
  defaults:
    SCRIPT_REPO_COMMIT: master
    # fake values. inheriting projects below should set reasonable values.
    lt_device_selector: "Samsung GZ4200-90"
    TASKCLUSTER_CLIENT_ID: tc-client-id-set-me
    # env var with key is looked for at this with underscores: `tc_worker_type_set_me`
    TC_WORKER_TYPE: tc-worker-type-set-me
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
  # test-1:
  #     SCRIPT_REPO_COMMIT: future_commit
  #     lt_device_selector: "Galaxy A51-11"
  #     TASKCLUSTER_CLIENT_ID: project/autophone/gecko-t-lambda-test-1
  #     TC_WORKER_TYPE: gecko-t-lambda-gw-test-1
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
"""


def test_load_file_config(tmp_path):
    """
    Tests that _load_file_config correctly loads configuration from an actual file.
    """
    # Create a temporary config file
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    config_file.write_text(SAMPLE_FILE_CONFIG_YAML)

    config_lt = ConfigurationLt()
    config_lt.configure(config_path=str(config_file))

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
