import time

from mozilla_bitbar_devicepool.lambdatest.job_tracker import JobTracker

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


class TestJobTracker:
    """Tests for JobTracker class."""

    def test_get_active_job_count_empty(self):
        """Test that get_active_job_count returns 0 when no jobs are tracked."""
        tracker = JobTracker()
        assert tracker.get_active_job_count() == 0

    def test_get_active_job_count_with_jobs(self):
        """Test that get_active_job_count returns correct count with active jobs."""
        tracker = JobTracker()
        # Add some jobs
        tracker.add_job_udids(["device1", "device2", "device3"])
        assert tracker.get_active_job_count() == 3

    def test_get_active_job_count_after_expiry(self, monkeypatch):
        """Test that get_active_job_count removes expired jobs and returns correct count."""
        # Create tracker with 1 second expiry for faster testing
        tracker = JobTracker(expiry_seconds=1)

        # Mock time.time to return controlled values
        current_time = time.time()
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Add some jobs at current time
        tracker.add_job_udids(["device1", "device2"])
        assert tracker.get_active_job_count() == 2

        # Advance time beyond expiry
        monkeypatch.setattr(time, "time", lambda: current_time + 2)

        # Should now return 0 as jobs expired
        assert tracker.get_active_job_count() == 0

    def test_get_active_job_count_mixed_expiry(self, monkeypatch):
        """Test that get_active_job_count correctly handles jobs with mixed expiry times."""
        tracker = JobTracker(expiry_seconds=10)

        # Start with a controlled time
        current_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Add initial jobs
        tracker.add_job_udids(["device1", "device2"])
        assert tracker.get_active_job_count() == 2

        # Advance time and add more jobs
        current_time += 5
        monkeypatch.setattr(time, "time", lambda: current_time)
        tracker.add_job_udids(["device3", "device4"])
        assert tracker.get_active_job_count() == 4

        # Advance time past first job expiry but not second
        current_time += 6
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Should now have only 2 jobs active (device3 and device4)
        assert tracker.get_active_job_count() == 2

        # Verify which devices are still active
        active_udids = tracker.get_active_udids()
        assert "device1" not in active_udids
        assert "device2" not in active_udids
        assert "device3" in active_udids
        assert "device4" in active_udids

    def test_add_duplicate_udid_updates_timestamp(self, monkeypatch):
        """Test that adding a job with a UDID already tracked updates its timestamp."""
        tracker = JobTracker(expiry_seconds=10)

        # Control time
        current_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Add initial job
        tracker.add_job_udids(["device1"])

        # Advance time almost to expiry
        current_time += 9
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Add same UDID again (should update timestamp)
        tracker.add_job_udids(["device1"])

        # Advance time past first timestamp but not second
        current_time += 2
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Device should still be active because timestamp was updated
        assert tracker.get_active_job_count() == 1
        assert "device1" in tracker.get_active_udids()

    def test__force_expiry(self, monkeypatch):
        """Test that force_expiry removes all tracked jobs."""
        tracker = JobTracker(expiry_seconds=1)

        # Mock time
        current_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Add some jobs
        tracker.add_job_udids(["device1", "device2"])
        assert tracker.get_active_job_count() == 2

        # Force expiry
        tracker._force_expire(["device1", "device2"])

        # Should now return 0 as jobs expired
        assert tracker.get_active_job_count() == 0

    # test is_udid_active()
    def test_is_udid_active(self):
        """Test that is_udid_active correctly identifies active UDIDs."""
        tracker = JobTracker(expiry_seconds=1)
        tracker.add_job_udids(["device1", "device2"])
        assert tracker.is_udid_active("device1") is True
        assert tracker.is_udid_active("device3") is False
        assert tracker.is_udid_active("device2") is True
        assert tracker.is_udid_active("device4") is False
        # Add a new UDID
        tracker.add_job_udids(["device3"])
        assert tracker.is_udid_active("device3") is True
        # Remove a UDID
        tracker._force_expire(["device1"])
        assert tracker.is_udid_active("device1") is False
        # Check if a UDID is active after expiry
        time.sleep(2)
        assert tracker.is_udid_active("device1") is False
        assert tracker.is_udid_active("device2") is False
        assert tracker.is_udid_active("device3") is False
        assert tracker.is_udid_active("device4") is False

    # test clear()
    def test_clear(self):
        """Test that clear removes all tracked jobs."""
        tracker = JobTracker()
        tracker.add_job_udids(["device1", "device2"])
        assert tracker.get_active_job_count() == 2
        tracker.clear()
        assert tracker.get_active_job_count() == 0
        assert tracker.get_active_udids() == []
        assert tracker.is_udid_active("device1") is False
        assert tracker.is_udid_active("device2") is False
        assert tracker.is_udid_active("device3") is False
        assert tracker.is_udid_active("device4") is False
        # Add a new UDID
        tracker.add_job_udids(["device3"])
        assert tracker.get_active_job_count() == 1
        assert tracker.is_udid_active("device3") is True
        # Clear again
        tracker.clear()
        assert tracker.get_active_job_count() == 0
        assert tracker.get_active_udids() == []
        assert tracker.is_udid_active("device1") is False
        assert tracker.is_udid_active("device2") is False

    def test_has_active_jobs(self, monkeypatch):
        """Test that has_active_jobs correctly reports if there are active jobs."""
        tracker = JobTracker(expiry_seconds=10)

        # Test with empty tracker
        assert tracker.has_active_jobs() is False

        # Test with active jobs
        tracker.add_job_udids(["device1", "device2"])
        assert tracker.has_active_jobs() is True

        # Test after jobs expire
        current_time = time.time()
        monkeypatch.setattr(time, "time", lambda: current_time + 11)
        assert tracker.has_active_jobs() is False

    def test_get_newest_job_time(self, monkeypatch):
        """Test that get_newest_job_time returns the most recent timestamp."""
        tracker = JobTracker(expiry_seconds=10)

        # Test with empty tracker
        assert tracker.get_newest_job_time() is None

        # Control time
        current_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Add initial job
        tracker.add_job_udids(["device1"])
        assert tracker.get_newest_job_time() == current_time

        # Add jobs at different times
        current_time += 5
        monkeypatch.setattr(time, "time", lambda: current_time)
        tracker.add_job_udids(["device2"])
        assert tracker.get_newest_job_time() == current_time

        # Add earlier job (should not change newest time)
        current_time -= 3
        monkeypatch.setattr(time, "time", lambda: current_time)
        tracker.add_job_udids(["device3"])
        assert tracker.get_newest_job_time() == current_time + 3

        # After all jobs expire
        current_time += 60
        monkeypatch.setattr(time, "time", lambda: current_time)
        assert tracker.get_newest_job_time() is None

    def test_get_time_remaining_seconds(self, monkeypatch):
        """Test that get_time_remaining_seconds calculates correct remaining time."""
        tracker = JobTracker(expiry_seconds=10)

        # Test with empty tracker
        assert tracker.get_time_remaining_seconds() == 0

        # Control time
        current_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Add a job
        tracker.add_job_udids(["device1"])

        # Check time immediately after adding job
        assert tracker.get_time_remaining_seconds() == 10

        # Check halfway through expiry
        monkeypatch.setattr(time, "time", lambda: current_time + 5)
        assert tracker.get_time_remaining_seconds() == 5

        # Check at expiry boundary
        monkeypatch.setattr(time, "time", lambda: current_time + 10)
        assert tracker.get_time_remaining_seconds() == 0

        # Check after expiry
        monkeypatch.setattr(time, "time", lambda: current_time + 15)
        assert tracker.get_time_remaining_seconds() == 0

        # Add new job and test again
        monkeypatch.setattr(time, "time", lambda: current_time + 20)
        tracker.add_job_udids(["device2"])
        assert tracker.get_time_remaining_seconds() == 10

    def test_format_time_remaining(self, monkeypatch):
        """Test that format_time_remaining correctly formats the time."""
        tracker = JobTracker(expiry_seconds=10)

        # Control time
        current_time = 1000.0
        monkeypatch.setattr(time, "time", lambda: current_time)

        # Test with empty tracker
        assert tracker.format_time_remaining() == "0m 0s"

        # Add a job
        tracker.add_job_udids(["device1"])

        # Test formatting different times
        assert tracker.format_time_remaining() == "0m 10s"

        # Test 1 minute 5 seconds
        tracker = JobTracker(expiry_seconds=65)
        tracker.add_job_udids(["device1"])
        assert tracker.format_time_remaining() == "1m 5s"

        # Test 2 minutes exactly
        tracker = JobTracker(expiry_seconds=120)
        tracker.add_job_udids(["device1"])
        assert tracker.format_time_remaining() == "2m 0s"

        # Test halfway expired
        tracker = JobTracker(expiry_seconds=120)
        tracker.add_job_udids(["device1"])
        monkeypatch.setattr(time, "time", lambda: current_time + 60)
        assert tracker.format_time_remaining() == "1m 0s"

        # Test fully expired
        monkeypatch.setattr(time, "time", lambda: current_time + 120)
        assert tracker.format_time_remaining() == "0m 0s"
