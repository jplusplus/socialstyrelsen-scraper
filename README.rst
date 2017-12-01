
This is a scraper for statistical data from the statistcial databases http://www.socialstyrelsen.se built on top of the `Statscraper package <https://github.com/jplusplus/statscraper>`.

Very much alpha. Only tested on a selected topics.

Install
-------

  pip install -r requirements.txt


Example usage
-------------

.. code:: python

  from socialstyrelsen import SocialstyrelsenScraper

  scraper = SocialstyrelsenScraper()
  scraper.items  # List databasese
  # [<SocialstyrelsenDataset: abort (Aborter)>, <SocialstyrelsenDataset: amning (Amning)>...]

  dataset = scraper.get("ekonomisktbistandmanad")  # Get a specific (by id)

  # Inpect dataset
  print dataset.dimensions
  # [<SocialstyrelsenDimension: MATT>, <SocialstyrelsenDimension: FOR>, <SocialstyrelsenDimension: LANGD>, <SocialstyrelsenDimension: OMR>, <SocialstyrelsenDimension: AGI>, <SocialstyrelsenDimension: AR>]

  print dataset.dimensions["OMR"].allowed_values
  # [<SocialstyrelsenDimensionValue: 0 (Hela Riket)>, <SocialstyrelsenDimensionValue: 1 (Stockholm)>, ...]

  # Make a query, you have to explicitly define all dimension values you want
  # to query.
  res = dataset.fetch({
      "TABELL": "1",
      "OMR": ["01", "03"],
      "MANAD": ["4", "5", "6"],
      "AR": "2017",
      "MATT": "1",
  })

  # Do something with the result
  df = res.pandas


TODO
----

- Currently only properly tested on "ekonomiskt bistånd"
- Handle large queries.
- Handle dimension labels


Develop
------

Run tests:

  make tests
