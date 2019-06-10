import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from classes import Map
from parsers import TessParser, AbbyParser
from typing import Dict, List, Tuple, Callable

# Parsers
tess_parser = TessParser()
abby_parser = AbbyParser()

# Parse Tesseract HOCR
'''
Each hocr file represents 1 page of structure:

<html>
  <head>
    <title>
    <body>
      <div class='ocr_page'...
'''
file_names = ['1.hocr', '2.hocr', '3.hocr']
trees = [ET.parse(file_name) for file_name in file_names]
roots = [tree.getroot() for tree in trees]
bodies = [root[1] for root in roots]
tess_pages = map(lambda body: [div for div in body][0], bodies)
tess_parsed: List = tess_parser.parse_pages(tess_pages)
if False:
    for tess_parsed_page in tess_parsed:
        tess_parser.pretty_print(tess_parsed_page)

# Parse ABBY
'''
All pages are within 1 html file
'''
soup = BeautifulSoup(open("page.html"), "html.parser")
body = soup.findChildren("body")[0]
abby_pages = body.findChildren(recursive=False)
abby_parsed: List = abby_parser.parse_pages(abby_pages)
if False:
    for abby_parsed_page in abby_parsed:
        abby_parser.pretty_print(abby_parsed_page)


# Comparison
map = Map()
map.compare(abby_parsed, tess_parsed)

