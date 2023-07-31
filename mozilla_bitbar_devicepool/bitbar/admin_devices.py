# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from mozilla_bitbar_devicepool import TESTDROID
from mozilla_bitbar_devicepool.util.template import get_filter


# 	https://mozilla.bitbar.com/cloud/api/v2/admin/device/statuses?sort=deviceName_a&offset=0&limit=10
def get_device_statuses(**kwargs):
    """Return list of matching Bitbar device_groups belonging to current user.

    :param **kwargs: keyword arguments containing fieldnames and
                     values with which to filter the devices to
                     be returned. If a fieldname is missing, it is
                     not used in the filter.
                     {
                       'displayname': str,
                       'id': int,
                       'ostype': str
                     }

    Examples:
       get_device_groups() # Return all device groups
       get_device_groups(displayname='pixel2-perf') # Return pixel2-perf device group.
    """
    fields = {"displayname": str, "id": int, "ostype": str}

    # GET
    # TODO: test if filter works
    filter = get_filter(fields, **kwargs)
    response = TESTDROID.get(
        "api/v2/admin/device/statuses", payload={"limit": 0, "filter": filter}
    )
    return response["data"]
