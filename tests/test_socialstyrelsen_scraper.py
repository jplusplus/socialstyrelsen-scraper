# encoding: utf-8
from unittest import TestCase
import pytest
from socialstyrelsen.scraper import SocialstyrelsenScraper, parse_result_table
from socialstyrelsen.exceptions import InvalidQuery, TooLargeQuery

class TestSocialstyrelsen(TestCase):

    def setUp(self):
        self.scraper = SocialstyrelsenScraper()

    def test_fetch_all_datasets(self):
        self.assertTrue(len(self.scraper.items))

    def test_fetch_dimensions(self):
        ds = self.scraper["ekonomisktbistandmanad"]
        assert len(ds.dimensions) == 15

    def test_get_hidden_inputs(self):
        ds = self.scraper["ekonomisktbistandmanad"]
        assert isinstance(ds.hidden_inputs, dict)
        assert ds.hidden_inputs["senastAR"] == "2017"

    def test_fetch_allowed_values(self):
        ds = self.scraper["ekonomisktbistandmanad"]
        assert len(ds.dimensions["MATT"].allowed_values) == 5

        for dim in ds.dimensions:
            for value in dim.allowed_values:
                assert value.value
                assert value.label
            assert len(dim.allowed_values) > 0


    def test_basic_query(self):
        ds = self.scraper["ekonomisktbistandmanad"]
        res = ds.fetch({
            "TABELL": "1",
            "OMR": ["01", "03"],
            "MANAD": ["4", "5", "6"],
            "AR": "2017",
            "MATT": "1",
        })
        assert res.pandas.shape[0] == 6

        res = ds.fetch({
            "TABELL": "1",
            "OMR": "*",
            "MANAD": "1",
            "AR": "2017",
            "MATT": "1",
        })
        assert res.pandas.shape[0] == 312


    def test_bad_queries(self):
        ds = self.scraper["ekonomisktbistandmanad"]

        # Get non-existing dimension
        with pytest.raises(InvalidQuery):
            ds.fetch({
                "FOO": ["1"],
            })

        # Get non-existing value
        with pytest.raises(InvalidQuery):
            ds.fetch({
                "AR": ["FOO"],
            })


    def test_large_query(self):
        ds = self.scraper["ekonomisktbistandmanad"]

        with pytest.raises(TooLargeQuery):
            ds.fetch({
                    "TABELL": "1",
                    "MANAD": "*",
                    "AR": "*",
                    "MATT": "*",
                    "OMR": "*",
            })




    def test_parse_result_table(self):
        # Parse a table with multi-index on both rows and cols.

        html = read_file("tests/data/result_table_multi_col_multi_row.html")
        data = parse_result_table(html)
        assert len(data) == 291 * 2 * 8

        html = read_file("tests/data/result_table_no_index_selectors.html")
        data = parse_result_table(html)
        assert len(data) == 3 * 31

def read_file(file_path):
    """Get content of file."""
    with open(file_path, "r") as f:
        return f.read().decode("utf-8")
