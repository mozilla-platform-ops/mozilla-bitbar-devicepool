import os
import tempfile
import time
from unittest import mock

import pytest

from mozilla_bitbar_devicepool.lambdatest import job_cleaner


def make_dir_with_mtime(base, name, mtime):
    path = os.path.join(base, name)
    os.mkdir(path)
    os.utime(path, (mtime, mtime))
    return path


def test_clean_up_removes_old_matching_dirs(tmp_path):
    # Setup
    pattern = "mozilla-lt-devicepool-job-dir"
    cleaner = job_cleaner.JobCleaner(path=str(tmp_path), pattern=pattern)
    now = time.time()
    old = now - 90000  # >1 day
    recent = now - 1000

    # Create dirs
    old_dir = make_dir_with_mtime(tmp_path, pattern + "-old", old)
    recent_dir = make_dir_with_mtime(tmp_path, pattern + "-recent", recent)
    nonmatching_dir = make_dir_with_mtime(tmp_path, "other-dir", old)

    with mock.patch.object(job_cleaner.JobCleaner, "remove_directory") as rm:
        cleaner.clean_up()
        rm.assert_called_once_with(str(old_dir))


def test_clean_up_does_not_remove_recent_or_nonmatching_dirs(tmp_path):
    pattern = "mozilla-lt-devicepool-job-dir"
    cleaner = job_cleaner.JobCleaner(path=str(tmp_path), pattern=pattern)
    now = time.time()
    recent = now - 1000
    nonmatching = now - 90000

    recent_dir = make_dir_with_mtime(tmp_path, pattern + "-recent", recent)
    nonmatching_dir = make_dir_with_mtime(tmp_path, "other-dir", nonmatching)

    with mock.patch.object(job_cleaner.JobCleaner, "remove_directory") as rm:
        cleaner.clean_up()
        rm.assert_not_called()


def test_is_old_directory_true_and_false(tmp_path):
    cleaner = job_cleaner.JobCleaner()
    dir_path = tmp_path / "testdir"
    dir_path.mkdir()
    now = time.time()
    old = now - 90000
    recent = now - 1000

    os.utime(dir_path, (old, old))
    assert cleaner.is_old_directory(str(dir_path)) is True

    os.utime(dir_path, (recent, recent))
    assert cleaner.is_old_directory(str(dir_path)) is False


def test_remove_directory_calls_shutil_rmtree():
    cleaner = job_cleaner.JobCleaner()
    with mock.patch("shutil.rmtree") as rmtree:
        cleaner.remove_directory("/some/path")
        rmtree.assert_called_once_with("/some/path")
