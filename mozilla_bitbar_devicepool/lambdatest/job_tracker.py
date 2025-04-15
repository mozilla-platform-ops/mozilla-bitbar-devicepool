# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import time
import logging


class JobTracker:
    """
    Tracks recently started jobs and automatically expires them after a set duration.
    Used to avoid starting too many jobs before existing ones have had time to claim tasks.
    """

    def __init__(self, expiry_seconds=210):  # Default 3.5 minutes (210 seconds)
        self.expiry_seconds = expiry_seconds
        self.jobs = {}  # Format: {timestamp: count}
        self.logger = logging.getLogger(__name__)

    def add_jobs(self, count):
        """
        Record that a number of jobs were started at the current time.

        Args:
            count (int): Number of jobs started
        """
        if count <= 0:
            return

        current_time = time.time()
        self.jobs[current_time] = count
        self.logger.debug(f"Added {count} job(s) at timestamp {current_time}")

    def get_active_job_count(self):
        """
        Returns the count of jobs that haven't expired yet and removes expired entries.

        Returns:
            int: Number of non-expired jobs
        """
        self._clean_expired()
        total = sum(self.jobs.values())
        self.logger.debug(f"Current active job count: {total}")
        return total

    def _clean_expired(self):
        """Remove job entries older than expiry_seconds."""
        current_time = time.time()
        expired_timestamps = []

        for timestamp, count in self.jobs.items():
            if current_time - timestamp > self.expiry_seconds:
                expired_timestamps.append(timestamp)

        for timestamp in expired_timestamps:
            count = self.jobs.pop(timestamp)
            self.logger.debug(f"Expired {count} job(s) from timestamp {timestamp}")

    def clear(self):
        """Clear all tracked jobs."""
        self.jobs.clear()
        self.logger.debug("Cleared all tracked jobs")
