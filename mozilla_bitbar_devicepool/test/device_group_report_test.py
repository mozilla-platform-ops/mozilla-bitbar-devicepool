# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from mozilla_bitbar_devicepool import device_group_report


data = """
device_groups:
  motog4-docker-builder-2:
    Docker Builder:
  test-1:
  test-2:
  test-3:
  a51-unit:
  a51-perf:
    a51-01:
    a51-02:
    a51-03:
    a51-04:
    a51-05:
    a51-06:
    a51-07:
    a51-08:
    a51-09:
    a51-10:
    a51-11:
    a51-12:
    a51-13:
    a51-14:
    a51-15:
    a51-16:
    a51-17:
    a51-18:
    a51-19:
    a51-20:
    a51-21:
    a51-22:
    a51-23:
    a51-24:
    a51-25:
    a51-26:
    a51-27:
    a51-28:
    a51-29:
    a51-30:
    a51-31:
    a51-32:
    a51-33:
    a51-34:
    a51-35:
    a51-36:
    a51-37:
    a51-38:
    a51-39:
    a51-40:
  pixel5-unit:
    pixel5-01:
    pixel5-02:
    pixel5-03:
    pixel5-04:
    pixel5-05:
    pixel5-06:
    pixel5-07:
    pixel5-08:
    pixel5-09:
    pixel5-10:
    pixel5-11:
    pixel5-12:
    pixel5-13:
    pixel5-14:
    pixel5-15:
    pixel5-16:
    pixel5-17:
  pixel5-perf:
    pixel5-18:
    pixel5-19:
  pixel6-unit:
  pixel6-perf:
    pixel6-01:
    pixel6-02:
    pixel6-03:
    pixel6-04:
  s21-unit:
  s21-perf:
    s21-01:
"""


def test_device_group_report_v2():
    dgr = device_group_report.DeviceGroupReport()
    dgr.get_report_dict_v2(injected_data=data)

    assert dgr.get_report_dict_v2(injected_data=data) == {
        "device_counts": {"a51": 40, "pixel5": 19, "pixel6": 4, "s21": 1},
        "pool_counts": {
            "a51-perf": 40,
            "pixel5-perf": 2,
            "pixel5-unit": 17,
            "pixel6-perf": 4,
            "s21-perf": 1,
        },
        "total_devices": 64,
    }
