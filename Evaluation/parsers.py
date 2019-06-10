import re
from bs4 import BeautifulSoup
from xml.etree.ElementTree import Element
from classes import Tess, Abby
from typing import Dict, List, Tuple, Callable
from classes import Tess, Abby
from utils import TessType, AbbyType

class TessParser:
    def __init__(self):
        self.bbox_regex = "bbox \d+ \d+ \d+ \d+"
        self.page_num_regex = "ppageno \d+"
        self.confidence_regex = "x_wconf \d+"

    def parse_pages(self, pages: List[Element]):
        return [self.parse_page(page) for page in pages]

    def parse_page(self, el: Element):
        assert(el.attrib["class"] == 'ocr_page')
        page_dim = self.get_attrs(el)["bounds"] # Page dimensions only available at page level

        def helper(el: Element):
            if el.attrib["class"] == "ocrx_word":
                if len(el.getchildren()) > 0: # Nested italics or bolded characters
                    attributes = self.get_attrs(el)
                    attributes["text"] = el.getchildren()[0].text
                    return Tess(attributes, page_dim)
                return Tess(self.get_attrs(el), page_dim)
            else:
                node = Tess(self.get_attrs(el), page_dim)
                children = []
                for child in el:
                    children.append(helper(child))
                node.set_children(children)
                return node
        return helper(el)


    def get_attrs(self, el: Element):
        title = el.attrib["title"]
        bounds = re.findall(self.bbox_regex, title)
        page_num = re.findall(self.page_num_regex, title)
        confidence = re.findall(self.confidence_regex, title)
        return {
            "class": el.attrib["class"],
            "id": el.attrib["id"],
            "bounds": bounds,
            "page_num": page_num,
            "confidence": confidence,
            "text": el.text
        }

    def pretty_print(self, parsed: Dict):

        def print_words(group: Tess, indentation):
            print("%s" % (indentation * "\t"), end="")
            for word in group.children:
                print(word.text, end=" ")
            print()

        def helper(root: Tess, indentation):
            if root.t_type == "ocr_line" or \
               root.t_type == "ocr_caption" or \
               root.t_type == "ocr_header" or \
               root.t_type == "ocr_textfloat":
                print("%s %s" % (indentation * "\t", root.t_type))
                print_words(root, indentation + 1)
            else:
                print("%s %s" % (indentation * "\t", root.t_type))
                for child in root.children:
                    helper(child, indentation + 1)

        helper(parsed, 0)


class AbbyParser:

    def __init__(self):
        return

    def parse_pages(self, bs_pages: List):
        return [self.parse_page(page) for page in bs_pages]


    def parse_page(self, bs_page: BeautifulSoup):

        assert(bs_page.name == "page")
        page = Abby(bs_page.attrs, AbbyType.PAGE)

        children: List = []
        for child in bs_page.findChildren(recursive=False):
            if child.name == 'p':
                page.add_child(self.parse_text_block(child))
            elif child.name == 'table':
                page.add_child(self.parse_table(child))

        page.pass_page_dim(page.page_width, page.page_height)
        page.process()
        return page


    def parse_table(self, bs_table: BeautifulSoup):
        bs_table_body = bs_table.findChildren(recursive=False)[0]
        table = Abby({}, AbbyType.TABLE)

        for bs_row in bs_table_body.findChildren(recursive=False):
            row = Abby({}, AbbyType.T_ROW)
            for bs_block in bs_row.findChildren(recursive=False):
                row.add_child(self.parse_text_block(bs_block))
            table.add_child(row)

        return table


    def parse_text_block(self, bs_textblock: BeautifulSoup):

        assert(bs_textblock.name == "p" and bs_textblock.attrs["blocktype"] == "Text" or
               bs_textblock.name == 'td')
        textblock = Abby(bs_textblock.attrs, AbbyType.P)

        els = bs_textblock.findChildren(recursive=False)
        current_word: Abby = Abby({}, AbbyType.WORD)
        current_line: Abby = Abby({}, AbbyType.LINE)
        for i in range(len(els)):
            el = els[i]
            if el.name == 'br': # Line break
                current_line.add_child(current_word)
                textblock.add_child(current_line)
                current_word = Abby({}, AbbyType.WORD)
                current_line = Abby({}, AbbyType.LINE)
            elif el.text == " " or el.text == "\n": # Space / Word end
                current_line.add_child(current_word)
                current_word = Abby({}, AbbyType.WORD)
            elif el.name == 'span': # Character
                char_attributes = el.attrs
                char_attributes["text"] = el.text
                char = Abby(char_attributes, AbbyType.CHAR)
                current_word.add_child(char)
            else:
                raise("CANNOT PARSE UNKNOWN TYPE")

        return textblock


    def pretty_print(self, page: Abby):
        assert(page.a_type == AbbyType.PAGE)

        def printer(el: Abby):
            if el.a_type == AbbyType.PAGE:
                [printer(textblock) for textblock in el.children]
            elif el.a_type == AbbyType.TABLE:
                [printer(row) for row in el.children]
            elif el.a_type == AbbyType.T_ROW:
                print("========= ROW ===========")
                [printer(textblock) for textblock in el.children]
            elif el.a_type == AbbyType.P:
                [printer(line) for line in el.children]
            elif el.a_type == AbbyType.LINE:
                [printer(word) for word in el.children]
                print() # For line break
            elif el.a_type == AbbyType.WORD:
                for char in el.children:
                    print(char.text, end="")
                print("", end=" ") # Space between words
            else:
                raise("CANNOT PRINT UNKNOWN TYPE")

        printer(page)

