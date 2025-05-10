import pytest

from mozilla_bitbar_devicepool.util import misc, template


class TestMisc:
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
