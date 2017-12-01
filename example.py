# encoding: utf-8
from socialstyrelsen import SocialstyrelsenScraper

scraper = SocialstyrelsenScraper()
dataset = scraper["ekonomisktbistandmanad"]
query = {
    "TABELL": "1", # "Biståndshushåll"
    "MATT": [
        "2",  # "Utbetalt ekonomiskt bistånd tkr",
    ],
    "OMR": "*",  # All regions
    "AR": "*",
    "MANAD": "*",
    "UTRIKES_HUSH": "*"
}

df = dataset.fetch(query).pandas
