#encoding:utf-8

from vantetider import VantetiderScraper
from vantetider.allowed_values import TYPE_OF_OVERBELAGGNING, PERIODS
import dataset

TOPIC = "Overbelaggning"

db = dataset.connect('sqlite:///vantetider.db')
table = db.create_table(TOPIC)
scraper = VantetiderScraper()
dataset = scraper.get(TOPIC)
years = [x.value for x in dataset.years]
regions = [x.value for x in dataset.regions]

for region in regions:
    for year in years:
        res = dataset.fetch({
            "year": year,
            "type_of_overbelaggning": [x[0] for x in TYPE_OF_OVERBELAGGNING],
            "period": PERIODS,
            "region": region,
            })
        df = res.pandas
        data = res.list_of_dicts
        table.insert_many(data)

import pdb; pdb.set_trace()
