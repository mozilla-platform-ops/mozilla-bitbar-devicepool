import os

import pytest

from mozilla_bitbar_devicepool.lambdatest import job_config

# goal: test lambdatest/job_config.py


@pytest.fixture
def user_script_dir():
    """Resolve a real shipped userscripts version dir so tests exercise the actual template."""
    here = os.path.dirname(os.path.realpath(__file__))
    pkg_root = os.path.abspath(os.path.join(here, ".."))
    return os.path.join(pkg_root, "lambdatest", "user_scripts", "v5-python_runtime")


# test return_config
def test_return_config(user_script_dir):
    tc_client_id = "test_client_id"
    tc_access_token = "test_access_token"
    tc_worker_type = "test_worker_type"
    lt_app_url = "https://example.com"
    device_type_and_os = ".*-.*"
    udid = "test_udid"
    concurrency = 1
    # test with all parameters
    config = job_config.return_config(
        tc_client_id,
        tc_access_token,
        tc_worker_type,
        lt_app_url,
        udid,
        concurrency,
        user_script_dir=user_script_dir,
    )
    # basic checks
    assert config is not None
    assert udid in config
    assert lt_app_url in config
    assert tc_client_id in config
    assert tc_access_token in config
    assert tc_worker_type in config
    assert device_type_and_os in config
    # more complex checks
    assert f'fixedIP: "{udid}"' in config
    # TODO: add more


def test_return_config_no_udid(user_script_dir):
    config = job_config.return_config(
        "cid",
        "tok",
        "wtype",
        "https://example.com",
        None,
        1,
        user_script_dir=user_script_dir,
    )
    # no-udid branch emits a bare "#" placeholder line, not a fixedIP directive
    assert 'fixedIP: "' not in config
    assert "\n    #\n" in config


def test_return_config_concurrency_three(user_script_dir):
    config = job_config.return_config(
        "cid",
        "tok",
        "wtype",
        "https://example.com",
        None,
        3,
        user_script_dir=user_script_dir,
    )
    assert "concurrency: 3" in config
    for i in range(3):
        assert f'echo "taskcluster generic-worker {i}"' in config


def test_return_config_uses_template_from_user_script_dir(tmp_path):
    """The template is loaded from <user_script_dir>/hyperexecute.yaml.tmpl — not hardcoded.

    This validates the version-resolution path: a synthetic dir with a unique marker template
    produces output containing that marker.
    """
    marker = "MARKER_FROM_SYNTHETIC_TMPL_8675309"
    tmpl_body = f"# {marker}\nconcurrency: $concurrency\n"
    (tmp_path / job_config.TEMPLATE_FILENAME).write_text(tmpl_body)

    config = job_config.return_config(
        "cid",
        "tok",
        "wtype",
        "https://example.com",
        None,
        1,
        user_script_dir=str(tmp_path),
    )
    assert marker in config
    assert "concurrency: 1" in config


def test_return_config_requires_user_script_dir():
    with pytest.raises(ValueError):
        job_config.return_config("cid", "tok", "wtype", "https://example.com", None, 1)


# test write_config
def test_write_config(tmp_path, user_script_dir):
    p = tmp_path / "he.yml"

    tc_client_id = "test_client_id"
    tc_access_token = "test_access_token"
    tc_worker_type = "test_worker_type"
    lt_app_url = "https://example.com"
    device_type_and_os = ".*-.*"
    udid = "test_udid"
    concurrency = 918
    # test with all parameters
    _blah = job_config.write_config(
        tc_client_id,
        tc_access_token,
        tc_worker_type,
        lt_app_url,
        udid,
        concurrency,
        user_script_dir=user_script_dir,
        path=p,
    )
    # open the file and check contents
    with open(p, "r") as f:
        config = f.read()
    # basic checks
    assert config is not None
    assert udid in config
    assert lt_app_url in config
    assert tc_client_id in config
    assert tc_access_token in config
    assert tc_worker_type in config
    assert device_type_and_os in config
    # more complex checks
    assert f'fixedIP: "{udid}"' in config
    assert f"concurrency: {concurrency}" in config
