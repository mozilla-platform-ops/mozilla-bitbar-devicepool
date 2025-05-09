import pytest
from unittest.mock import patch
from mozilla_bitbar_devicepool.lambdatest.status import Status
import os


# Sample mock data
@pytest.fixture
def mock_jobs_data():
    # load this from a file (test_data/lt_get_jobs_1.txt) and use it
    this_file_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(this_file_dir, "test_data", "lt_get_jobs_shortened.txt")
    with open(data_path) as f:
        # evaluate it as a dict and return it
        return eval(f.read())


@pytest.fixture
def mock_jobs_data_with_initiated():
    # load this from a file (test_data/lt_get_jobs_1.txt) and use it
    this_file_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(this_file_dir, "test_data", "lt_get_jobs_2.txt")
    with open(data_path) as f:
        # evaluate it as a dict and return it
        return eval(f.read())


@pytest.fixture
def mock_devices_data():
    this_file_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(this_file_dir, "test_data", "lt_get_devices_1.txt")
    with open(data_path) as f:
        return eval(f.read())


@pytest.fixture
def status_instance():
    return Status("test_user", "test_key")


class TestStatus:
    def test_init(self):
        status = Status("test_user", "test_key")
        assert status.lt_username == "test_user"
        assert status.lt_api_key == "test_key"

    # verify the mock is working basically
    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_jobs")
    def test_get_jobs(self, mock_get_jobs, status_instance, mock_jobs_data):
        mock_get_jobs.return_value = mock_jobs_data
        result = status_instance.get_jobs(jobs=50)
        mock_get_jobs.assert_called_once_with("test_user", "test_key", jobs=50)
        assert result == mock_jobs_data

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_jobs")
    def test_get_job_dict(self, mock_get_jobs, status_instance, mock_jobs_data):
        mock_get_jobs.return_value = mock_jobs_data
        result = status_instance.get_job_dict(jobs=50)
        mock_get_jobs.assert_called_once_with("test_user", "test_key", jobs=50)
        expected = {
            9821: "running",
            9816: "completed",
            9812: "failed",
            9813: "completed",
            9815: "running",
            9775: "aborted",
            9790: "lambda_error",
            9766: "timeout",
        }
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_jobs")
    def test_get_job_summary(self, mock_get_jobs, status_instance, mock_jobs_data):
        mock_get_jobs.return_value = mock_jobs_data
        result = status_instance.get_job_summary(jobs=50)
        mock_get_jobs.assert_called_once_with("test_user", "test_key", label_filter_arr=None, jobs=50)
        expected = {"running": 2, "completed": 2, "failed": 1, "aborted": 1, "lambda_error": 1, "timeout": 1}
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_jobs")
    def test_get_initiated_job_count(self, mock_get_jobs, status_instance, mock_jobs_data_with_initiated):
        mock_get_jobs.return_value = mock_jobs_data_with_initiated
        result = status_instance.get_initiated_job_count(jobs=50)
        mock_get_jobs.assert_called_once_with("test_user", "test_key", label_filter_arr=None, jobs=50)
        # The initiated job has Tasks=3
        assert result == 2

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.get_jobs")
    # def test_get_running_job_count(self, mock_get_jobs, status_instance, mock_jobs_data):
    #     mock_get_jobs.return_value = mock_jobs_data
    #     result = status_instance.get_running_job_count(jobs=50)
    #     mock_get_jobs.assert_called_once_with("test_user", "test_key", label_filter_arr=None, jobs=50)
    #     # One running job with Tasks=1 and one with Tasks=2 but only 1 in_progress
    #     assert result == 2

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    # def test_get_device_list(self, mock_get_devices, status_instance, mock_devices_data):
    #     mock_get_devices.return_value = mock_devices_data
    #     result = status_instance.get_device_list()
    #     mock_get_devices.assert_called_once_with("test_user", "test_key")
    #     expected = {"Galaxy A55 5G": {"RXYA1821": "online", "RXYA1823": "busy"}, "Galaxy A51": {"DB123212": "online"}}
    #     assert result == expected

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    # def test_get_device_list_with_filter(self, mock_get_devices, status_instance, mock_devices_data):
    #     mock_get_devices.return_value = mock_devices_data
    #     result = status_instance.get_device_list(device_type_and_os_filter="Galaxy A55 5G-14")
    #     mock_get_devices.assert_called_once_with("test_user", "test_key")
    #     expected = {"Galaxy A55 5G": {"RXYA1821": "online", "RXYA1823": "busy"}}
    #     assert result == expected

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    # def test_get_device_state_summary(self, mock_get_devices, status_instance, mock_devices_data):
    #     mock_get_devices.return_value = mock_devices_data
    #     result = status_instance.get_device_state_summary()
    #     expected = {"online": 2, "busy": 1}
    #     assert result == expected

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    # def test_get_device_state_summary_with_filter(self, mock_get_devices, status_instance, mock_devices_data):
    #     mock_get_devices.return_value = mock_devices_data
    #     result = status_instance.get_device_state_summary(device_type_and_os_filter="Galaxy A55 5G-14")
    #     expected = {"online": 1, "busy": 1}
    #     assert result == expected

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    # def test_get_device_state_summary_by_device(self, mock_get_devices, status_instance, mock_devices_data):
    #     mock_get_devices.return_value = mock_devices_data
    #     result = status_instance.get_device_state_summary_by_device()
    #     expected = {"Galaxy A55 5G": {"online": 1, "busy": 1}, "Galaxy A51": {"online": 1}}
    #     assert result == expected

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    # def test_get_device_state_count(self, mock_get_devices, status_instance, mock_devices_data):
    #     mock_get_devices.return_value = mock_devices_data
    #     result = status_instance.get_device_state_count("Galaxy A55 5G-14", "online")
    #     assert result == 1

    #     result = status_instance.get_device_state_count("Galaxy A55 5G-14", "busy")
    #     assert result == 1

    #     # Test with a non-existent state
    #     result = status_instance.get_device_state_count("Galaxy A55 5G-14", "offline")
    #     assert result == 0

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    # def test_empty_response(self, mock_get_devices, status_instance):
    #     mock_get_devices.return_value = None
    #     result = status_instance.get_device_list()
    #     assert result == {}

    # @patch("mozilla_bitbar_devicepool.lambdatest.status.Status")
    # @patch("os.environ", {"LT_USERNAME": "test_user", "LT_ACCESS_KEY": "test_key"})
    # def test_lt_status_main(self, mock_status):
    #     status_instance = MagicMock()
    #     mock_status.return_value = status_instance

    #     status_instance.get_device_state_summary.return_value = {"online": 2, "busy": 1}
    #     status_instance.get_running_job_count.return_value = 1

    #     # No warning should be printed as there are running jobs
    #     lt_status_main()

    #     # Test busy devices with no running jobs scenario
    #     status_instance.get_running_job_count.return_value = 0
    #     status_instance.get_device_list.return_value = {"Galaxy A55 5G": {"RXYA1823": "busy"}}

    #     lt_status_main()
