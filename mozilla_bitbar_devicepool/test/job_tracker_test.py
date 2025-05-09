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
