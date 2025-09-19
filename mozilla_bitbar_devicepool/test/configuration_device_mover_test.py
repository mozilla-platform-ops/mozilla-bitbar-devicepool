import difflib
import os
import shutil

import pytest

from mozilla_bitbar_devicepool.configuration_device_mover import ConfigurationDeviceMover

TEST_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "./test_data/configs/test_config.yml")
TEST_CONFIG_PATH_2 = os.path.join(os.path.dirname(__file__), "./test_data/configs/test_config_2.yml")

TEST_CONFIG_PATH_2_EXPECTED = os.path.join(os.path.dirname(__file__), "./test_data/configs/test_config_2_EXPECTED.yml")

TEST_CONFIG_COPY = os.path.join(os.path.dirname(__file__), "./test_data/configs/test_config_copy.yml")
TEST_CONFIG_COPY_2 = os.path.join(os.path.dirname(__file__), "./test_data/configs/test_config_2_copy.yml")


# function that compares two files and checks that they are identical
def compare_files(file1, file2, verbose=False):
    # load both files
    with open(file1, "r") as f1, open(file2, "r") as f2:
        content1 = f1.readlines()
        content2 = f2.readlines()

    if verbose:
        # show both files
        print(f"File 1 ({file1}):\n{''.join(content1)}\n")
        print(f"File 2 ({file2}):\n{''.join(content2)}\n")

    # if they are the same, return True
    # show output if they differ
    if content1 != content2:
        diff = "".join(difflib.unified_diff(content1, content2, fromfile=file1, tofile=file2))
        raise AssertionError(f"Files {file1} and {file2} differ:\n{diff}")
    return True


@pytest.fixture(autouse=True)
def setup_and_teardown(debugging=True):
    # clean up any existing test copies (do this now vs after yield so we can debug issues)
    if debugging:
        try:
            os.remove(TEST_CONFIG_COPY)
            os.remove(TEST_CONFIG_COPY_2)
        except FileNotFoundError:
            pass
    # Copy the config file for each test to avoid modifying the original
    shutil.copyfile(TEST_CONFIG_PATH, TEST_CONFIG_COPY)
    shutil.copyfile(TEST_CONFIG_PATH_2, TEST_CONFIG_COPY_2)
    yield
    if not debugging:
        os.remove(TEST_CONFIG_COPY)
        os.remove(TEST_CONFIG_COPY_2)


def test_load_config():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY, backup=False)
    config = mover.load_config()
    assert "device_groups" in config
    assert "groupA" in config["device_groups"]


def test_list_device_groups():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY, backup=False)
    mover.load_config()
    groups = mover.list_device_groups()
    assert set(groups) == {"groupA", "groupB", "groupC"}


def test_list_devices_in_group():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY, backup=False)
    mover.load_config()
    devices = mover.list_devices_in_group("groupA")
    assert set(devices) == {"device1", "device2"}
    devices = mover.list_devices_in_group("groupC")
    assert devices == []


def test_find_device_group():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY, backup=False)
    mover.load_config()
    assert "groupA" in mover.find_device_groups("device1")
    assert "groupB" in mover.find_device_groups("device3")
    assert mover.find_device_groups("unknown") == []


def test_move_devices():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY, backup=False)
    mover.load_config()
    result = mover.move_devices("groupA", "groupB", ["device1"], dry_run=True)
    assert "device1" in result["moved"]
    # Actually move
    result = mover.move_devices("groupA", "groupB", ["device1"])
    assert "device1" in result["moved"]
    assert "groupB" in mover.find_device_groups("device1")


# if a project is not active, a dupe can exist in the config... (perhaps a bug? or feature?)
# so test that moving a device that is duped removes it from all groups except the target
def test_move_devices_with_dupe():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY_2, backup=False)
    mover.load_config()
    # move device1 to groupC
    result = mover.move_devices_from_any_pool("groupC", ["device1"])
    import pprint

    pprint.pprint(result)
    assert "device1" in result["moved"]
    assert mover.find_device_groups("device1") == ["groupC"]


def test_move_devices_from_any_pool():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY, backup=False)
    mover.load_config()
    result = mover.move_devices_from_any_pool("groupC", ["device2"])
    assert "device2" in result["moved"]
    assert "groupC" in mover.find_device_groups("device2")


def test_validate_device_list():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY, backup=False)
    mover.load_config()
    validation = mover.validate_device_list(["device1", "device3", "unknown"])
    assert "groupA" in validation["found"]["device1"] or "groupB" in validation["found"]["device1"]  # may have moved
    assert "groupB" in validation["found"]["device3"]
    assert "unknown" in validation["not_found"]


def test_save_config_retains_empty_groups():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY, backup=False)
    mover.load_config()
    # Remove all devices from groupC
    mover.config_data["device_groups"]["groupC"] = {}
    mover.save_config()
    mover.load_config()
    # Assert that groupC still exists but is empty
    assert "groupC" in mover.config_data["device_groups"]
    assert mover.config_data["device_groups"]["groupC"] == {}


def test_cmopare_files_works():
    # identical files
    assert compare_files(TEST_CONFIG_PATH, TEST_CONFIG_PATH)
    # different files
    with pytest.raises(AssertionError):
        compare_files(TEST_CONFIG_PATH, TEST_CONFIG_PATH_2, verbose=True)


# move device6 to groupB
#   - ensure groupC still exists with its comment
#   - ensure groupC is not defined as `{}`
def test_exact_file_after_move():
    mover = ConfigurationDeviceMover(TEST_CONFIG_COPY_2, backup=False)
    mover.load_config()
    # move device6 to groupB
    mover.move_devices_from_any_pool("groupB", ["device6"], comment="gorilla")
    # compare the modified config file to the expected file
    assert compare_files(TEST_CONFIG_COPY_2, TEST_CONFIG_PATH_2_EXPECTED)
