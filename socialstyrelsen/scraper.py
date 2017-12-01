# encoding: utf-8
import requests
from copy import deepcopy
from bs4 import BeautifulSoup
import re
from statscraper import (BaseScraper, Collection, DimensionValue,
                         Dataset, Dimension, Result)
from statscraper.exceptions import NoSuchItem
from socialstyrelsen.exceptions import InvalidQuery, TooLargeQuery

BASE_URL = u"http://sdb.socialstyrelsen.se/"


class SocialstyrelsenScraper(BaseScraper):

    def _fetch_itemslist(self, current_item):
        url = "http://www.socialstyrelsen.se/statistik/statistikdatabas/"
        # Get start page
        html = self._get_html(url)
        soup = BeautifulSoup(html, 'html.parser')
        for a_tag in soup.select("a[href*=/statistik/statistikdatabas]"):
            id_ = a_tag.get("href").replace("/statistik/statistikdatabas/", "")
            label = a_tag.text.strip()
            if "default.aspx" in id_:
                # catch link to index page
                continue

            yield SocialstyrelsenDataset(id_, label=label)

    def _fetch_dimensions(self, dataset):
        soup = dataset.soup
        for elem in soup.select(".dia_valj_ram"):
            dim_elem = elem.select_one(".fontText")
            #label = dim_elem.text.strip()
            id_ = dim_elem.select_one("span").get("id").split("_")[2].upper() # "ph1_Val_dia_lblRubrikVal"
            dim = SocialstyrelsenDimension(id_.upper())#, label=label
            dim.elem = elem
            yield dim

        for elem in soup.select("select"):
            id_ = elem.get("name")
            dim = SocialstyrelsenDimension(id_)
            dim.elem = elem
            yield dim


    def _fetch_allowed_values(self, dimension):
        soup = dimension.elem
        if dimension.elem_type == "checkbox_list":
            for a_tag in soup.select("a[href*=cc]"):
                # u"javascript:cc('i_00_1')" => "00"
                value = a_tag.get("href").split("_")[1]
                label = a_tag.text.strip()
                dim_value = SocialstyrelsenDimensionValue(value, dimension, label)
                yield dim_value

        elif dimension.elem_type == "select":
            for option_tag in soup.select("option"):
                value = option_tag.get("value")
                label = option_tag.text.strip()
                dim_value = SocialstyrelsenDimensionValue(value, dimension, label)
                yield dim_value




    def _fetch_data(self, dataset, query):
        """

        """
        url = dataset.url.replace("val", "resultat")

        # Start building the POST payload from values of hidden inputs
        payload = dataset.hidden_inputs
        query_size = 1
        for dim_key, values in query.items():
            # Get dimensions from query by id
            # Will error on bad query
            try:
                dim = dataset.dimensions[dim_key]
            except NoSuchItem:
                dim_ids = [x.id for x in dataset.dimensions]
                msg = "{} is not a valid dimension id. Try: ".format(dim_key,
                                                                     dim_ids)
                raise InvalidQuery(msg)

            if values == "*":
                values = [x.value for x in dim.allowed_values]
            elif not isinstance(values, list):
                values = [values]
            query_values = []
            for val in values:
                # validate the value passed used in query
                # will error if invalid value
                try:
                    dim_value = dim.allowed_values[val]
                except StopIteration:  # Odd exception from statscraper
                    dim_value = dim.allowed_values.get_by_label(val)
                    if dim_value is None:
                        msg = "{} is not an allowed value or label for {}. Try: {}"\
                            .format(val, dim_key, dim.allowed_values)
                        raise InvalidQuery(msg)

                query_values.append(dim_value.in_query)

            query_size *= len(query_values)
            query_value = "".join(query_values)  # ";01;;02;;03;"

            payload[dim.query_key] = query_value

        # Socialstyrelsen has a limit of 50 000 datapoints per query
        # TODO: Split into multiple queries automatically
        MAX_QUERY_SIZE = 50000
        if query_size > MAX_QUERY_SIZE:
            msg = ("Your query was too large: {}, threshold is {}. "
                   "Try splitting it into multiple queries.")\
                   .format(query_size, MAX_QUERY_SIZE)
            raise TooLargeQuery(msg)

        html = self._post_html(url, payload)

        # Check if the result is an error page
        error_msg = re.search("Fel med nummer (-?\d+)", html)
        if error_msg:
            # TODO: Find out what these error codes mean.
            # Known codes are -1  and 10.
            error_code = error_msg.group(1)
            msg = "Result page didn't render. Socialstyrelsen error code: {}".format(error_code)
            raise InvalidQuery(msg)

        for value, index in parse_result_table(html):
            yield Result(value, index)

    # HELPER METHODS
    def _get_html(self, url):
        """ Get html from url
        """
        self.log.info(u"/GET {}".format(url))
        r = requests.get(url)
        if hasattr(r, 'from_cache'):
            if r.from_cache:
                self.log.info("(from cache)")

        r.raise_for_status()

        return r.content

    def _post_html(self, url, payload):
        self.log.info(u"/POST {} with {}".format(url, payload))
        r = requests.post(url, payload)
        r.raise_for_status()

        return r.content


    @property
    def log(self):
        if not hasattr(self, "_logger"):
            self._logger = PrintLogger()
        return self._logger


class SocialstyrelsenDataset(Dataset):
    @property
    def html(self):
        pass

    @property
    def url(self):
        """The query ui is embeded in an iframe. Get the url of that iframe.
        """
        if not hasattr(self, "_url"):
            wrapper_url = "http://www.socialstyrelsen.se/statistik/statistikdatabas/{}".format(self.id)
            html = self.scraper._get_html(wrapper_url)
            soup = BeautifulSoup(html, 'html.parser')
            self._url = soup.select_one("iframe").get("src")

        return self._url

    @property
    def html(self):
        """Get html content of query interface."""
        if not hasattr(self, "_html"):
            self._html = self.scraper._get_html(self.url)
        return self._html

    @property
    def soup(self):
        """Soupify html."""
        return BeautifulSoup(self.html, 'html.parser')

    @property
    def hidden_inputs(self):
        """Get default values of hidden input fields as dict, keys being
        `name` attribute of html tag and values `value` attribute.
        {
            "senastAR": "2017",
            "senastMANAD": "8",
        }
        """
        return dict((x.get("name"), x.get("value", "")) for x in self.soup.select("input[type=hidden]"))


class SocialstyrelsenDimension(Dimension):

    @property
    def elem_type(self):
        """There are two kinds of dimension elements in the ui:
        1) Checkboxlist (often used for regions)
        2) Basic selects (used most commonly)

        :returns: "checkbox_list" | "select"
        """
        if self.elem.get("class") and "dia_valj_ram" in self.elem.get("class"):
            elem_type = "checkbox_list"
        elif self.elem.name == "select":
            elem_type = "select"
        else:
            raise Exception("Unknown elem type: {}".format(self.elem))

        return elem_type

    @property
    def is_multivalue(self):
        """Can we use multiple values in query on this dimension?"""
        if self.elem_type == "checkbox_list":
            return True
        elif self.elem_type == "select":
            return self.elem.get("multiple")
        else:
            raise Exception("Unknown elem type: {}".format(self.elem))

    @property
    def query_key(self):
        key = self.id
        # In some cases we need to use a different dimension key in the post
        # payload than in the form.
        TRANSLATE_DIMS = {
            "UTRIKES_HUSH": "UTRIKES"  # "dim_key" : "payload_key"
        }
        if key in TRANSLATE_DIMS:
            key = TRANSLATE_DIMS[key]

        if self.elem_type == "checkbox_list":
            query_key = "hv{}".format(key)
        else:
            query_key = "v{}".format(key)

        return query_key


class SocialstyrelsenDimensionValue(DimensionValue):
    @property
    def in_query(self):
        if self.dimension.is_multivalue:
            return ";{};".format(self.value)
        else:
            return self.value


def parse_result_table(html):
    """Parse values from table. Returns a list of values and corresponding index.

    [
        (123, { "OMR": "01", "AR": "2017", "MANAD": "01"})
    ]
    """
    data = []
    soup = BeautifulSoup(html, 'html.parser')

    column_selector = soup.select_one("#ph1_ddlTabellKolumn")
    if column_selector:
        # CASE 1: This is result page has only a column selector
        option_elems = column_selector.select("option")
        assert len(option_elems) == 2

        row_index = None
        col_index = None
        for option_elem in option_elems:
            if option_elem.get("selected"):
                col_index = [option_elem.get("value")]
            else:
                row_index = [option_elem.get("value")]

        assert row_index is not None
        assert col_index is not None

    else:
        # CASE 2: This resulta page has both row and column selctor
        # Get the dimensions broadcasted as rows
        row_index_elems = soup.select("#ph1_ListBoxRader option")
        assert len(row_index_elems) > 0, "Row selector missing on result page"
        row_index = [x.get("value") for x in row_index_elems]  # ['OMR', 'UTR']

        # Get the dimensions broadcasted as columns
        col_index_elems = soup.select("#ph1_ListBoxKolumner option")
        assert len(col_index_elems) > 0, "Column selector missing on result page"
        col_index = [x.get("value") for x in col_index_elems]  # ['AR', 'MANAD']

    # Hackish: Translate the dimension keys used in row/column selector
    # Struggling to see why to naming of dimensions differ accross the site
    def translate_dim(dim_key):
        DIM_TRANSLATIONS = {
            "UTR": "UTRIKES_HUSH"
        }
        if dim_key in DIM_TRANSLATIONS:
            return DIM_TRANSLATIONS[dim_key]
        else:
            return dim_key
    col_index = [translate_dim(x) for x in col_index]
    row_index = [translate_dim(x) for x in row_index]

    # Get html table
    table = soup.select_one("#ph1_pnlTabellResultat table")
    assert table, "Result table is missing"

    title_rows = table.select("tr")[:len(col_index)]  # rows with headings
    value_rows = table.select("tr")[len(col_index):]  # rows with values
    n_table_cols = len(value_rows[0].select("td"))  # total number of columns
    n_value_cols = n_table_cols - len(row_index)  # number of cols with values

    # Construct a pandas-like index for row
    col_index_values = []
    for tr in title_rows:
        cells = tr.select("td, th")
        # Odd html structure, on some title rows first cells are merged
        if n_table_cols == len(cells):
            offset = len(row_index)
        else:
            # ...in others not.
            offset = 1

        level_values = []
        for cell in cells[offset:]:
            # Cells can be merged with colspan
            n = int(float(cell.get("colspan", "1")))
            value = cell.text.strip()
            level_values += n * [value]

        assert len(level_values) == n_value_cols
        col_index_values.append(level_values)

    # Final col_index_values will look something like this:
    # [(u'2017', u'Januari'), (u'2017', u'Februari'), (u'2017', u'Mars')]
    col_index_values = zip(*col_index_values)
    assert len(col_index_values) == n_value_cols

    # Start parsing data
    for tr in value_rows:
        value_cells = tr.select("td")[len(row_index):]
        assert len(value_cells) == n_value_cols

        # Get current row index
        row_index_cells = tr.select("td")[:len(row_index)]
        row_index_values = [x.text.strip() for x in row_index_cells]
        row_dims = dict(zip(row_index, row_index_values))

        for i, cell in enumerate(value_cells):
            value, status = parse_cell_value(cell.text)
            # TODO: Handle status

            dims = deepcopy(row_dims)
            col_dims = dict(zip(col_index, col_index_values[i]))
            dims.update(col_dims)

            data.append((value, dims))

    return data

def parse_cell_value(val):
    """Parse value from table cell.

    >>>parse_cell_value("5.4")
    (5.4, None)

    >>>parse_cell_value("5 432")
    (5432.0, None)

    >>>parse_cell_value("--")
    (None, "Saknas")

    :param val (str): cell content
    :returns (tuple): value and status as tuple
    """
    missing_codes = {
        "X": "Sekretess",
        "--": "Saknas",
    }
    if val in missing_codes.keys():
        return None, missing_codes[val]
    else:
        val = float(val.replace(u"\xa0", ""))
        return val, None

class PrintLogger():
    """ Empyt "fake" logger
    """

    def log(self, msg, *args, **kwargs):
        print msg

    def debug(self, msg, *args, **kwargs):
        print msg

    def info(self, msg, *args, **kwargs):
        print msg

    def warning(self, msg, *args, **kwargs):
        print msg

    def error(self, msg, *args, **kwargs):
        print msg

    def critical(self, msg, *args, **kwargs):
        print msg
