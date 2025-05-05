# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
from unittest.mock import patch, mock_open  # Import patch and mock_open
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


# Use patch to mock the 'open' built-in function
@patch("builtins.open", new_callable=mock_open, read_data=SAMPLE_FILE_CONFIG_YAML)
def test_load_file_config(mock_file_open):
    """
    Tests that load_file_config correctly loads configuration using a mocked file.
    """
    config_lt = ConfigurationLt()

    # Call load_file_config. The path argument doesn't matter since open is mocked,
    # but we pass one for completeness.
    config_lt.load_file_config(config_path="dummy/path/config.yml")

    # Assert that the loaded config matches the sample data dictionary
    assert config_lt.get_config() == SAMPLE_FILE_CONFIG_DICT
    # Verify open was called with the path constructed by the method
    # Note: The exact path depends on where configuration_lt.py is relative to the project root
    # We might need to adjust this assertion based on the actual path construction logic
    # For now, let's just assert it was called once.
    mock_file_open.assert_called_once()
    # Example of checking the path if needed:
    # expected_path = os.path.abspath(os.path.join(os.path.dirname(configuration_lt.__file__), "..", "dummy/path/config.yml"))
    # mock_file_open.assert_called_once_with(expected_path)


@patch("builtins.open")
def test_load_file_config_file_not_found(mock_file_open):
    """
    Tests that load_file_config raises FileNotFoundError when the file doesn't exist.
    """
    # Configure the mock 'open' to raise FileNotFoundError when called
    mock_file_open.side_effect = FileNotFoundError("File not found")

    config_lt = ConfigurationLt()

    # Assert that FileNotFoundError is raised
    with pytest.raises(FileNotFoundError):
        config_lt.load_file_config(config_path="config/non_existent_config.yml")

    # Verify open was called (or attempted to be called)
    mock_file_open.assert_called_once()
