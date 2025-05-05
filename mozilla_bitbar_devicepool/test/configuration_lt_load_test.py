# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from mozilla_bitbar_devicepool.configuration_lt import ConfigurationLt

# Sample configuration data as a dictionary (for assertion)
SAMPLE_FILE_CONFIG_DICT = {
    "projects": {
        "defaults": {"default_key": "default_value"},
        "projectC": {"specific_key": "specific_value"},
    },
    "device_groups": {
        "projectC": "udid5 udid6",
    },
    "some_other_top_level_key": "value123",
}

# Sample configuration data as a raw YAML string (for writing to file)
SAMPLE_FILE_CONFIG_YAML = """
projects:
  defaults:
    default_key: default_value
  projectC:
    specific_key: specific_value
device_groups:
  projectC: udid5 udid6
some_other_top_level_key: value123
"""


def test_load_file_config(tmp_path):
    """
    Tests that load_file_config correctly loads configuration from an actual file.
    """
    # Create a temporary config file
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yml"
    config_file.write_text(SAMPLE_FILE_CONFIG_YAML)

    config_lt = ConfigurationLt()

    # Call load_file_config with the path to the temporary file
    config_lt.load_file_config(config_path=str(config_file))

    # Assert that the loaded config matches the sample data dictionary
    assert config_lt.get_config() == SAMPLE_FILE_CONFIG_DICT


def test_load_file_config_file_not_found(tmp_path):
    """
    Tests that load_file_config raises FileNotFoundError when the file doesn't exist.
    """
    config_lt = ConfigurationLt()

    # Define a path that does not exist within the temporary directory
    non_existent_path = tmp_path / "non_existent_config.yml"

    # Assert that FileNotFoundError is raised when trying to load a non-existent file
    with pytest.raises(FileNotFoundError):
        config_lt.load_file_config(config_path=str(non_existent_path))
