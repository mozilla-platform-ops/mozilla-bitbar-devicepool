from datetime import datetime, timezone


# Get the current date in UTC in an ISO formatted string
def get_utc_date_string():
    utc_now = datetime.now(timezone.utc)
    utc_date_iso = utc_now.isoformat(timespec="seconds")
    return utc_date_iso


# pip install GitPython
import git


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
