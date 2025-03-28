def shorten_worker_type(worker_type):
    """Shorten the worker type for display."""
    worker_type_short = worker_type.replace("gecko-t-lambda-", "")
    return worker_type_short
