from mozilla_bitbar_devicepool.lambdatest import job_config

# goal: test lambdatest/job_config.py


# test return_config
def test_return_config():
    tc_client_id = "test_client_id"
    tc_access_token = "test_access_token"
    tc_worker_type = "test_worker_type"
    lt_app_url = "https://example.com"
    device_type_and_os = "Galaxy A55 5G-14"
    udid = "test_udid"
    concurrency = 1
    # test with all parameters
    config = job_config.return_config(
        tc_client_id,
        tc_access_token,
        tc_worker_type,
        lt_app_url,
        device_type_and_os,
        udid,
        concurrency,
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


# # test write_config
# def test_write_config():
#     # test with all parameters
#     config = job_config.write_config(
#         tc_client_id="test_client_id",
#         tc_access_token="test_access_token",
