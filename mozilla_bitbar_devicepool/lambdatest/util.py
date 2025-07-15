# TODO: move these to the common util module (mozilla_bitbar_devicepool/util)


def shorten_worker_type(worker_type):
    """Shorten the worker type for display."""
    worker_type_short = worker_type.replace("gecko-t-lambda-", "")
    return worker_type_short


def array_key_search(prefix_match, search_array):
    """Search for a prefix match in an array of strings."""
    # print(f"sa {search_array}")
    # print(type(search_array))
    for item in search_array:
        # print(item)
        if item.startswith(prefix_match):
            return item
    return None


# example input: ["tcdp","a55-perf","R5CXC1PW7CR"]
# should return "R5CXC1PW7CR"
def get_device_from_job_labels(job_labels):
    if not job_labels:
        return None
    # find the first label that looks like a device udid
    for label in job_labels:
        if label == "tcdp":
            continue  # skip tcdp label
        if "unit" in label or "perf" in label:
            continue
        else:
            return label
    return None


# e.g. '["tcdp","a55-perf","R5CXC1PW7CR"]' to ['tcdp', 'a55-perf', 'R5CXC1PW7CR']
def string_list_to_list(string_list):
    """Convert a string representation of a list to an actual list."""
    if not string_list:
        return []
    # remove brackets
    string_list = string_list.strip("[]")
    if not string_list:
        return []
    # split by comma
    items = string_list.split(",")
    # strip whitespace and quotes
    items = [item.strip().strip('"').strip("'") for item in items]
    return items
