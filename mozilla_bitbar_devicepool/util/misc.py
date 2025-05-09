import uuid as uuidlib
from datetime import datetime, timezone

import git
import humanhash


# Get the current date in UTC in an ISO formatted string
def get_utc_date_string():
    utc_now = datetime.now(timezone.utc)
    utc_date_iso = utc_now.isoformat(timespec="seconds")
    return utc_date_iso


def get_git_info():
    repo = git.Repo(search_parent_directories=True)
    sha = repo.head.object.hexsha
    dirty = repo.is_dirty()

    short_sha = sha[:7]

    if dirty:
        return f"{short_sha}-dirty"
    else:
        return f"{short_sha}"


# print(get_git_info())


def humanhash_from_string(value, **params):
    """
    Generate a UUID with a human-readable representation from an input string.
    Returns `human_repr`.  Accepts the same keyword arguments as :meth:`humanize`
    """

    digest = str(uuidlib.uuid5(uuidlib.NAMESPACE_DNS, value)).replace("-", "")
    return humanhash.humanize(digest, **params)


# main
if __name__ == "__main__":
    print(get_utc_date_string())
    print(get_git_info())
    print(humanhash_from_string("hello world"))
    #
    print(humanhash_from_string("hello world", words=1))
    print(humanhash_from_string("hello world", words=2))
    print(humanhash_from_string("hello world", words=2))
    #
    print(humanhash_from_string("hello world", words=3))
    print(humanhash_from_string("hello world", words=3))
    #
    print(humanhash_from_string("hello world", words=4))
    print(humanhash_from_string("hello world", words=5))
    print(humanhash_from_string("hello world", words=6))
    print(humanhash_from_string("hello world", words=7))
    print(humanhash_from_string("hello world", words=8))
