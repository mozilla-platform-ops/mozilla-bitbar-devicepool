import git  # Add this import
import pytest

from mozilla_bitbar_devicepool.util import misc, template


class TestUtilTemplate:
    def test_lookup_key_value(self):
        dict_list = [{"key1": "value1"}, {"key2": "value2"}]
        result = template.lookup_key_value(dict_list, "key1")
        assert result == "value1"

        result = template.lookup_key_value(dict_list, "key3")
        assert result is None

    def test_get_filter(self):
        fields = {"field1": str, "field2": int, "field3": bool}
        kwargs = {"field1": "value1", "field2": 42, "field3": True}
        result = template.get_filter(fields, **kwargs)
        assert result == ["s_field1_eq_value1", "n_field2_eq_42", "b_field3_eq_True"]

    def test_apply_dict_defaults(self):
        input_dict = {"key1": {"subkey3": "value1"}}
        defaults_dict = {"key1": {"subkey1": "aaa", "subkey2": "dddd"}}
        result = template.apply_dict_defaults(input_dict, defaults_dict)
        assert result == {"key1": {"subkey1": "aaa", "subkey2": "dddd", "subkey3": "value1"}}


class TestUtilMisc:
    def test_get_utc_date_string(self):
        result = misc.get_utc_date_string()
        assert isinstance(result, str)
        assert "+00:00" in result
        assert result.endswith("+00:00")

    def test_get_git_info(self, mocker):
        mock_repo = mocker.patch("git.Repo")
        mock_repo.return_value.head.object.hexsha = "1234567890abcdef"
        mock_repo.return_value.is_dirty.return_value = False
        result = misc.get_git_info()
        assert result == "1234567"
        # test dirty repo
        mock_repo.return_value.is_dirty.return_value = True
        result = misc.get_git_info()
        assert result == "1234567-dirty"
        # TODO: work on these tests
        #
        # # test empty repo
        # mock_repo.side_effect = git.exc.InvalidGitRepositoryError
        # result = misc.get_git_info()
        # assert result == "None"
        # # test no repo
        # mock_repo.side_effect = git.exc.NoSuchPathError
        # result = misc.get_git_info()
        # assert result == "None"
        # # test no git
        # mock_repo.side_effect = git.exc.GitCommandError
        # mock_repo.return_value = None
        # result = misc.get_git_info()
        # assert result == "None"

    def test_humanhash_from_string(self):
        result = misc.humanhash_from_string("hello world")
        assert isinstance(result, str)
