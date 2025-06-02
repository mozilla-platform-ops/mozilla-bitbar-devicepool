# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil
import time


class JobCleaner:
    """
    A class to handle the cleanup of LambdaTest jobs.
    This class is responsible for cleaning up jobs that are no longer needed.
    """

    def __init__(self, path="/tmp", pattern="mozilla-lt-devicepool-job-dir"):
        """
        Initialize the JobCleaner.

        This constructor sets up the necessary parameters for the job cleanup.
        """
        self.cleaning_path = path
        self.cleaning_pattern = pattern

    def clean_up(self):
        """
        Perform the cleanup operation for the specified job.
        This method should contain the logic to clean up the job resources.
        """
        result_stats = {
            "removed": 0,  # directories removed
            "matched": 0,  # matched the cleaning pattern, but not old enough to remove
            "not_matched": 0,  # did not match the cleaning pattern
            "total_inspected": 0,  # total directories inspected
        }

        # remove directories older than 1 day that match the cleaning pattern
        for dirpath, dirnames, filenames in os.walk(self.cleaning_path):
            for dirname in dirnames:
                result_stats["total_inspected"] += 1
                if dirname.startswith(self.cleaning_pattern):
                    result_stats["matched"] += 1
                    dir_to_check = os.path.join(dirpath, dirname)
                    if self.is_old_directory(dir_to_check):
                        self.remove_directory(dir_to_check)
                        result_stats["removed"] += 1
                else:
                    result_stats["not_matched"] += 1

        return result_stats

    def is_old_directory(self, dir_path):
        """
        Check if a directory is older than 1 day.

        Args:
            dir_path (str): The path of the directory to check.

        Returns:
            bool: True if the directory is older than 1 day, False otherwise.
        """
        dir_age = time.time() - os.path.getmtime(dir_path)
        return dir_age > 86400  # 86400 seconds in a day

    def remove_directory(self, dir_path):
        """
        Remove a directory and all its contents.

        Args:
            dir_path (str): The path of the directory to remove.
        """
        shutil.rmtree(dir_path)


# main
if __name__ == "__main__":
    cleaner = JobCleaner()
    print(
        f"Starting cleanup of old LambdaTest job directories in {cleaner.cleaning_path}/{cleaner.cleaning_pattern}..."
    )
    result_statistics = cleaner.clean_up()
    print("Cleanup completed. Results: ")
    for key, value in result_statistics.items():
        print(f"  {key}: {value}")
