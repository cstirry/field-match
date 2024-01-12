#!/usr/bin/env python

import unittest

import pandas as pd

from src.field_match.field_match import (
    compute_text_similarity,
    compute_date_similarity,
    compute_boolean_similarity,
    compute_numeric_similarity,
    compute_categorical_similarity,
    field_similarity_report,
    generate_column_rename
)


class TestFieldMatch(unittest.TestCase):
    """Tests for `field_match` package."""

    def test_compute_text_similarity(self):
        series_1 = pd.Series(["apple", "banana", "cherry"])
        series_2 = pd.Series(["apple pie", "banana split"])
        result = compute_text_similarity(series_1, series_2)
        self.assertTrue(0 <= result <= 1)

    def test_compute_date_similarity(self):
        series_1 = pd.to_datetime(pd.Series(["2021-01-01", "2021-01-02", "2021-01-03"]))
        series_2 = pd.to_datetime(pd.Series(["2021-01-01", "2000-12-07"]))
        result = compute_date_similarity(series_1, series_2)
        self.assertTrue(0 <= result <= 1)

    def test_compute_boolean_similarity(self):
        series_1 = pd.Series([True, False, True])
        series_2 = pd.Series([True, True])
        result = compute_boolean_similarity(series_1, series_2)
        self.assertTrue(0 <= result <= 1)

    def test_compute_numeric_similarity(self):
        series_1 = pd.Series([1, 2, 3])
        series_2 = pd.Series([2, 3, 4])
        result = compute_numeric_similarity(series_1, series_2)
        self.assertTrue(0 <= result <= 1)

    def test_compute_categorical_similarity(self):
        series_1 = pd.Series(["cat", "dog", "bird"])
        series_2 = pd.Series(["dog", "fly"])
        result = compute_categorical_similarity(series_1, series_2)
        self.assertTrue(0 <= result <= 1)

    def test_field_similarity_report(self):
        # Create sample data
        data1 = pd.DataFrame({'A': ['apple', 'banana'], 'B': [1, 2]})
        data2 = pd.DataFrame({'X': ['apple pie', 'banana bread'], 'Y': [2, 3]})

        # Test field_similarity_report
        report = field_similarity_report(data1, data2)
        self.assertIsInstance(report, dict)
        self.assertIn('A', report)
        self.assertIn('B', report)

    def test_generate_column_rename(self):
        # Sample output from field_similarity_report
        report = {
            'A': {'data_type': 'int64', 'similar_fields': [('D', 0.9), ('E', 0.3)]},
            'B': {'data_type': 'object', 'similar_fields': [('F', 0.6), ('G', 0.1)]},
            'C': {'data_type': 'object', 'similar_fields': [('F', 0.2), ('G', 0.1)]},
        }

        # Test generate_column_rename_snippet
        snippet = generate_column_rename(report)
        print(snippet)
        self.assertIsInstance(snippet, str)
        self.assertIn("'D': 'A'", snippet)
        self.assertIn("'F': 'B'", snippet)


if __name__ == '__main__':
    unittest.main()
