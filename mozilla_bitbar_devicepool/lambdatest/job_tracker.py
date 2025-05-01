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

    # Default 3.5 minutes (210 seconds)
    # 4 minutes
    def __init__(self, expiry_seconds=(4 * 60)):
        self.expiry_seconds = expiry_seconds
        self.job_timestamps = []
        self.job_udids = {}  # New dictionary to map timestamps to UDIDs
        self.logger = logging.getLogger(__name__)

    def add_jobs(self, count, udids=None):
        """
        Record that a number of jobs were started at the current time.

        Args:
            count (int): Number of jobs started
            udids (list, optional): List of UDIDs associated with jobs, must be same length as count if provided
        """
        if count <= 0:
            return

        now = time.time()

        if udids and len(udids) != count:
            self.logger.warning(
                f"UDID list length ({len(udids)}) doesn't match job count ({count}). UDIDs may not be properly tracked."
            )

        for i in range(count):
            timestamp = now
            self.job_timestamps.append(timestamp)

            # Store UDID if provided
            if udids and i < len(udids):
                self.job_udids[timestamp] = udids[i]

        self.logger.debug(f"Added {count} job(s) at timestamp {now}")

    def get_active_job_count(self):
        """
        Returns the count of jobs that haven't expired yet and removes expired entries.

        Returns:
            int: Number of non-expired jobs
        """
        self._clean_expired()
        total = len(self.job_timestamps)
        self.logger.debug(f"Current active job count: {total}")
        return total

    def get_active_udids(self):
        """
        Get list of UDIDs that are still considered active (not expired).

        Returns:
            list: List of active UDIDs
        """
        self._clean_expired()
        return list(self.job_udids.values())

    def is_udid_active(self, udid):
        """
        Check if a UDID is currently active in any job.

        Args:
            udid (str): The UDID to check

        Returns:
            bool: True if UDID is active, False otherwise
        """
        self._clean_expired()
        return udid in self.job_udids.values()

    def _clean_expired(self):
        """Remove job entries older than expiry_seconds."""
        now = time.time()
        expired_indices = []

        for i, timestamp in enumerate(self.job_timestamps):
            if now - timestamp > self.expiry_seconds:
                expired_indices.append(i)

        # Remove expired timestamps and their UDIDs
        if expired_indices:
            # Remove from timestamps list
            new_timestamps = [ts for i, ts in enumerate(self.job_timestamps) if i not in expired_indices]

            # Remove from UDIDs dict
            expired_timestamps = [self.job_timestamps[i] for i in expired_indices]
            for ts in expired_timestamps:
                if ts in self.job_udids:
                    del self.job_udids[ts]

            self.job_timestamps = new_timestamps

    def clear(self):
        """Clear all tracked jobs."""
        self.job_timestamps.clear()
        self.job_udids.clear()
        self.logger.debug("Cleared all tracked jobs")
