import pytest

from mozilla_bitbar_devicepool.lambdatest.util import array_key_search, shorten_worker_type


def test_shorten_worker_type_removes_prefix():
    assert shorten_worker_type("gecko-t-lambda-android") == "android"
    assert shorten_worker_type("gecko-t-lambda-foo-bar") == "foo-bar"


def test_shorten_worker_type_no_prefix():
    assert shorten_worker_type("android") == "android"
    assert shorten_worker_type("lambda-android") == "lambda-android"


def test_array_key_search_found():
    arr = ["foo", "bar", "baz", "prefix-match", "other"]
    assert array_key_search("prefix", arr) == "prefix-match"
    assert array_key_search("ba", arr) == "bar"


def test_array_key_search_not_found():
    arr = ["foo", "bar", "baz"]
    assert array_key_search("qux", arr) is None
    assert array_key_search("", arr) == "foo"  # empty prefix matches first


def test_array_key_search_empty_array():
    assert array_key_search("foo", []) is None
