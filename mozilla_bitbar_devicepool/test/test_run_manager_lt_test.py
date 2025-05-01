# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import pytest
from unittest.mock import patch

# Add the parent directory to sys.path to allow importing the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mozilla_bitbar_devicepool.test_run_manager_lt import TestRunManagerLT


# TODO: convert shared data to use multiprocessing.Manager
#    - avoid having to deal with locking
#
#   ```Option 2: Thread-safe Collections
#     Using multiprocessing.Manager for shared state:
#    ```


@pytest.fixture
def test_manager():
    """Create a test instance of TestRunManagerLT with mocked dependencies."""
    with patch("mozilla_bitbar_devicepool.test_run_manager_lt.configuration_lt") as mock_config:
        with patch("mozilla_bitbar_devicepool.test_run_manager_lt.status") as _mock_status:
            # Create instance with mocked dependencies
            mock_config.ConfigurationLt.return_value.lt_username = "mock_username"
            mock_config.ConfigurationLt.return_value.lt_access_key = "mock_access_key"
            mock_config.ConfigurationLt.return_value.config = {"projects": {}}
            manager = TestRunManagerLT(debug_mode=True)
            yield manager


def test_calculate_jobs_to_start_basic(test_manager):
    """Test basic functionality of calculate_jobs_to_start."""
    # Test with simple values
    result = test_manager.calculate_jobs_to_start(5, 10)
    assert result == 5, "Should return 5 (tc_jobs_not_handled is smallest)"

    result = test_manager.calculate_jobs_to_start(10, 5)
    assert result == 5, "Should return 5 (available_devices_count is smallest)"

    result = test_manager.calculate_jobs_to_start(20, 20, 10)
    assert result == 10, "Should return 10 (max_jobs is smallest)"


def test_calculate_jobs_to_start_edge_cases(test_manager):
    """Test edge cases for calculate_jobs_to_start."""
    # Test with zero values
    result = test_manager.calculate_jobs_to_start(0, 10)
    assert result == 0, "Should return 0 when no pending TC jobs"

    result = test_manager.calculate_jobs_to_start(10, 0)
    assert result == 0, "Should return 0 when no available devices"

    # Test with negative values
    result = test_manager.calculate_jobs_to_start(-5, 10)
    assert result == 0, "Should handle negative TC jobs and return 0"


def test_calculate_jobs_to_start_default_max(test_manager):
    """Test that the default max_jobs is used when not specified."""
    # Set a custom max_jobs_to_start on the manager
    test_manager.max_jobs_to_start = 7

    # Test that it uses the manager's max_jobs_to_start by default
    result = test_manager.calculate_jobs_to_start(10, 10)
    assert result == 7, "Should use max_jobs_to_start from class instance"

    # Test that explicitly passed max_jobs overrides the default
    result = test_manager.calculate_jobs_to_start(10, 10, 3)
    assert result == 3, "Should use explicitly provided max_jobs"


def test_calculate_jobs_to_start_large_values(test_manager):
    """Test with large values to ensure correct behavior."""
    result = test_manager.calculate_jobs_to_start(1000, 1000, 500)
    assert result == 500, "Should handle large values correctly"

    # Test with large max_jobs_to_start
    test_manager.max_jobs_to_start = 1000
    result = test_manager.calculate_jobs_to_start(50, 100)
    assert result == 50, "Should use tc_jobs_not_handled when it's smallest"
