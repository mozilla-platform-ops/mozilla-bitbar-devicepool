import pytest

from mozilla_bitbar_devicepool.test_run_manager_lt import TestRunManagerLT


@pytest.fixture
def test_manager():
    """Create and return a TestRunManagerLT instance for testing."""
    # Create manager with debug_mode=True to skip hyperexecute binary check
    return TestRunManagerLT(unit_testing_mode=True)


def test_calculate_jobs_to_start_basic(test_manager):
    """Test basic calculation of jobs to start."""
    # When we have 5 TC jobs and 10 available devices, should start 5 jobs (up to max_jobs)
    assert test_manager.calculate_jobs_to_start(5, 10, 0, 10) == 5

    # When we have 15 TC jobs but only 10 available devices, should start 10 jobs
    assert test_manager.calculate_jobs_to_start(15, 10, 0, 20) == 10

    # When we have 15 TC jobs and 20 available devices but max_jobs is 10, should start 10 jobs
    assert test_manager.calculate_jobs_to_start(15, 20, 0, 10) == 10


def test_calculate_jobs_to_start_no_jobs_needed(test_manager):
    """Test calculation when no jobs are needed."""
    # When there are no TC jobs pending
    assert test_manager.calculate_jobs_to_start(0, 10, 0, 10) == 0

    # When there are negative TC jobs (shouldn't happen in practice)
    assert test_manager.calculate_jobs_to_start(-5, 10, 0, 10) == 0


def test_calculate_jobs_to_start_no_devices(test_manager):
    """Test calculation when no devices are available."""
    # When there are no available devices
    assert test_manager.calculate_jobs_to_start(5, 0, 0, 10) == 0


def test_calculate_jobs_to_start_max_initiated_jobs(test_manager):
    """Test that no jobs are started if global_initiated exceeds GLOBAL_MAX_INITITATED_JOBS."""
    # Define the constant locally for clarity and isolation, using a representative value.
    # This avoids depending on the exact value defined in the TestRunManagerLT class.
    GLOBAL_MAX_INITITATED_JOBS = 40

    # When global_initiated exceeds GLOBAL_MAX_INITITATED_JOBS
    assert test_manager.calculate_jobs_to_start(5, 10, GLOBAL_MAX_INITITATED_JOBS + 1, 10) == 0

    # When global_initiated equals MAX_INITITATED_JOBS (should still allow jobs)
    assert test_manager.calculate_jobs_to_start(5, 10, GLOBAL_MAX_INITITATED_JOBS, 10) == 5

    # When global_initiated is just below GLOBAL_MAX_INITITATED_JOBS
    assert test_manager.calculate_jobs_to_start(5, 10, GLOBAL_MAX_INITITATED_JOBS - 1, 10) == 5


def test_calculate_jobs_to_start_default_max_jobs(test_manager):
    """Test using the default max_jobs."""
    # With default max_jobs, should use test_manager.max_jobs_to_start
    assert test_manager.calculate_jobs_to_start(20, 20, 0) == min(20, test_manager.max_jobs_to_start)

    # When TC jobs and available devices exceed default max_jobs
    default_max = test_manager.max_jobs_to_start
    assert test_manager.calculate_jobs_to_start(default_max + 5, default_max + 10, 0) == default_max


def test_calculate_jobs_to_start_edge_cases(test_manager):
    """Test edge cases for job calculation."""
    # All zeros
    assert test_manager.calculate_jobs_to_start(0, 0, 0, 0) == 0

    # All high numbers but limited by max_jobs
    assert test_manager.calculate_jobs_to_start(100, 100, 0, 5) == 5

    # All high numbers but limited by TC jobs
    assert test_manager.calculate_jobs_to_start(3, 100, 0, 50) == 3

    # All high numbers but limited by available devices
    assert test_manager.calculate_jobs_to_start(100, 4, 0, 50) == 4
