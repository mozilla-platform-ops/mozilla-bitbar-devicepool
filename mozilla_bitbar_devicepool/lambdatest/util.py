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
