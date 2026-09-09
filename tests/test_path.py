"""Run: python tests/test_path.py"""
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from portable.path import PathError, resolve


class TestResolve(unittest.TestCase):
    def test_top_level_key(self):
        self.assertEqual(resolve({"email": "a@b.com"}, "email"), "a@b.com")

    def test_nested_key(self):
        self.assertEqual(resolve({"user": {"email": "a@b.com"}}, "user.email"), "a@b.com")

    def test_list_index(self):
        self.assertEqual(resolve({"orders": [10, 20]}, "orders[1]"), 20)

    def test_key_then_index_then_key(self):
        doc = {"orders": [{"id": 1}, {"id": 2}]}
        self.assertEqual(resolve(doc, "orders[1].id"), 2)

    def test_missing_top_level_key_names_it_in_the_error(self):
        with self.assertRaises(PathError) as ctx:
            resolve({}, "email")
        self.assertIn("email", str(ctx.exception))

    def test_missing_nested_key_names_the_full_path_walked(self):
        with self.assertRaises(PathError) as ctx:
            resolve({"user": {}}, "user.email")
        self.assertIn("user.email", str(ctx.exception))

    def test_index_out_of_range(self):
        with self.assertRaises(PathError):
            resolve({"orders": [1]}, "orders[5]")

    def test_indexing_a_non_list_is_a_path_error_not_a_crash(self):
        with self.assertRaises(PathError):
            resolve({"orders": "not a list"}, "orders[0]")

    def test_keying_into_a_non_dict_is_a_path_error_not_a_crash(self):
        with self.assertRaises(PathError):
            resolve({"user": "just a string"}, "user.email")

    def test_keying_into_a_list_directly_is_a_path_error(self):
        with self.assertRaises(PathError):
            resolve([1, 2, 3], "email")


if __name__ == "__main__":
    unittest.main()
