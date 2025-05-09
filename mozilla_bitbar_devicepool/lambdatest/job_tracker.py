# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import time


# TODO: rename to DeviceJobTracker? DeviceRecentlyStartedJobTracker?
#
# DeviceRecentlyStartedJobTracker really, but JobTracker is shorter
class JobTracker:
    """
    Keeps track of devices with recently started jobs.

    After the configured time, they will expire and be removed from the tracker.

    This is used to avoid starting another job on a device that we've already assigned, but hasn't claimed
    a TC task yet.
    """

    # Default 3.5 minutes (210 seconds)
    # 4 minutes
    def __init__(self, expiry_seconds=(4 * 60)):
        self.expiry_seconds = expiry_seconds
        self.job_timestamps = {}  # Changed to dict mapping UDIDs to timestamps
        self.logger = logging.getLogger(__name__)

    def add_job_udids(self, udids):
        """
        Record that jobs with specific UDIDs were started at the current time.

        Args:
            udids (list): List of UDIDs associated with jobs
        """
        now = time.time()

        # Store timestamp for each UDID
        for udid in udids:
            self.job_timestamps[udid] = now

        # self.logger.debug(f"Added {len(udids)} job(s) with UDIDs {', '.join(udids).lstrip(' ')} at timestamp {now}")

    def get_active_job_count(self):
        """
        Returns the count of jobs that haven't expired yet and removes expired entries.

        Returns:
            int: Number of non-expired jobs
        """
        self._clean_expired()
        total = len(self.job_timestamps)
        # self.logger.debug(f"Current active job count: {total}")
        return total

    def get_active_udids(self):
        """
        Get list of UDIDs that are still considered active (not expired).

        Returns:
            list: List of active UDIDs
        """
        self._clean_expired()
        return list(self.job_timestamps.keys())

    def is_udid_active(self, udid):
        """
        Check if a UDID is currently active in any job.

        Args:
            udid (str): The UDID to check

        Returns:
            bool: True if UDID is active, False otherwise
        """
        self._clean_expired()
        return udid in self.job_timestamps

    def _clean_expired(self):
        """Remove job entries older than expiry_seconds."""
        now = time.time()
        expired_udids = []

        for udid, timestamp in self.job_timestamps.items():
            if now - timestamp > self.expiry_seconds:
                expired_udids.append(udid)

        # Remove expired timestamps
        for udid in expired_udids:
            del self.job_timestamps[udid]

    # for testing only
    def _force_expire(self, udid_list):
        """Force expiration of jobs for testing purposes."""
        for udid in udid_list:
            if udid in self.job_timestamps:
                del self.job_timestamps[udid]

    def clear(self):
        """Clear all tracked jobs."""
        self.job_timestamps.clear()
        self.logger.debug("Cleared all tracked jobs")
