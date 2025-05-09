import pytest
from unittest.mock import patch, MagicMock
from mozilla_bitbar_devicepool.lambdatest.status import Status, lt_status_main


# Sample mock data
@pytest.fixture
def mock_jobs_data():
    return {
        "data": [
            {
                "job_number": "1",
                "status": "running",
                "job_label": "test-label-1",
                "Tasks": "1",
            },
            {
                "job_number": "2",
                "status": "completed",
                "job_label": "test-label-2",
                "Tasks": "1",
            },
            {
                "job_number": "3",
                "status": "initiated",
                "job_label": "test-label-3",
                "Tasks": "3",
            },
            {
                "job_number": "4",
                "status": "running",
                "job_label": "test-label-4",
                "Tasks": "2",
                "job_summary": {"scenario_stage_summary": {"status_counts_excluding_retries": {"in_progress": "1"}}},
            },
        ]
    }


@pytest.fixture
def mock_devices_data():
    return {
        "data": {
            "private_cloud_devices": [
                {"name": "Galaxy A55 5G", "udid": "RXYA1821", "status": "online", "fullOsVersion": "14"},
                {"name": "Galaxy A55 5G", "udid": "RXYA1823", "status": "busy", "fullOsVersion": "14"},
                {"name": "Galaxy A51", "udid": "DB123212", "status": "online", "fullOsVersion": "12"},
            ]
        }
    }


@pytest.fixture
def status_instance():
    return Status("test_user", "test_key")


class TestStatus:
    def test_init(self):
        status = Status("test_user", "test_key")
        assert status.lt_username == "test_user"
        assert status.lt_api_key == "test_key"

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
        expected = {"1": "running", "2": "completed", "3": "initiated", "4": "running"}
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_jobs")
    def test_get_job_summary(self, mock_get_jobs, status_instance, mock_jobs_data):
        mock_get_jobs.return_value = mock_jobs_data
        result = status_instance.get_job_summary(jobs=50)
        mock_get_jobs.assert_called_once_with("test_user", "test_key", label_filter_arr=None, jobs=50)
        expected = {"running": 2, "completed": 1, "initiated": 1}
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_jobs")
    def test_get_initiated_job_count(self, mock_get_jobs, status_instance, mock_jobs_data):
        mock_get_jobs.return_value = mock_jobs_data
        result = status_instance.get_initiated_job_count(jobs=50)
        mock_get_jobs.assert_called_once_with("test_user", "test_key", label_filter_arr=None, jobs=50)
        # The initiated job has Tasks=3
        assert result == 3

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_jobs")
    def test_get_running_job_count(self, mock_get_jobs, status_instance, mock_jobs_data):
        mock_get_jobs.return_value = mock_jobs_data
        result = status_instance.get_running_job_count(jobs=50)
        mock_get_jobs.assert_called_once_with("test_user", "test_key", label_filter_arr=None, jobs=50)
        # One running job with Tasks=1 and one with Tasks=2 but only 1 in_progress
        assert result == 2

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    def test_get_device_list(self, mock_get_devices, status_instance, mock_devices_data):
        mock_get_devices.return_value = mock_devices_data
        result = status_instance.get_device_list()
        mock_get_devices.assert_called_once_with("test_user", "test_key")
        expected = {"Galaxy A55 5G": {"RXYA1821": "online", "RXYA1823": "busy"}, "Galaxy A51": {"DB123212": "online"}}
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    def test_get_device_list_with_filter(self, mock_get_devices, status_instance, mock_devices_data):
        mock_get_devices.return_value = mock_devices_data
        result = status_instance.get_device_list(device_type_and_os_filter="Galaxy A55 5G-14")
        mock_get_devices.assert_called_once_with("test_user", "test_key")
        expected = {"Galaxy A55 5G": {"RXYA1821": "online", "RXYA1823": "busy"}}
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    def test_get_device_state_summary(self, mock_get_devices, status_instance, mock_devices_data):
        mock_get_devices.return_value = mock_devices_data
        result = status_instance.get_device_state_summary()
        expected = {"online": 2, "busy": 1}
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    def test_get_device_state_summary_with_filter(self, mock_get_devices, status_instance, mock_devices_data):
        mock_get_devices.return_value = mock_devices_data
        result = status_instance.get_device_state_summary(device_type_and_os_filter="Galaxy A55 5G-14")
        expected = {"online": 1, "busy": 1}
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    def test_get_device_state_summary_by_device(self, mock_get_devices, status_instance, mock_devices_data):
        mock_get_devices.return_value = mock_devices_data
        result = status_instance.get_device_state_summary_by_device()
        expected = {"Galaxy A55 5G": {"online": 1, "busy": 1}, "Galaxy A51": {"online": 1}}
        assert result == expected

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    def test_get_device_state_count(self, mock_get_devices, status_instance, mock_devices_data):
        mock_get_devices.return_value = mock_devices_data
        result = status_instance.get_device_state_count("Galaxy A55 5G-14", "online")
        assert result == 1

        result = status_instance.get_device_state_count("Galaxy A55 5G-14", "busy")
        assert result == 1

        # Test with a non-existent state
        result = status_instance.get_device_state_count("Galaxy A55 5G-14", "offline")
        assert result == 0

    @patch("mozilla_bitbar_devicepool.lambdatest.status.get_devices")
    def test_empty_response(self, mock_get_devices, status_instance):
        mock_get_devices.return_value = None
        result = status_instance.get_device_list()
        assert result == {}

    @patch("mozilla_bitbar_devicepool.lambdatest.status.Status")
    @patch("os.environ", {"LT_USERNAME": "test_user", "LT_ACCESS_KEY": "test_key"})
    def test_lt_status_main(self, mock_status):
        status_instance = MagicMock()
        mock_status.return_value = status_instance

        status_instance.get_device_state_summary.return_value = {"online": 2, "busy": 1}
        status_instance.get_running_job_count.return_value = 1

        # No warning should be printed as there are running jobs
        lt_status_main()

        # Test busy devices with no running jobs scenario
        status_instance.get_running_job_count.return_value = 0
        status_instance.get_device_list.return_value = {"Galaxy A55 5G": {"RXYA1823": "busy"}}

        lt_status_main()
