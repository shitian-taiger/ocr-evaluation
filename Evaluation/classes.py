from typing import Dict, List, Tuple, Callable
from bs4 import BeautifulSoup
from utils import TessType, AbbyType
from collections import defaultdict

class Tess:

    def __init__(self, attrs: Dict, page_dim: List):
        self.page_dims = page_dim
        self.page_width, self.page_height = [int(b) for b in page_dim[0].split(" ")[-2:]]
        self.t_type = attrs["class"]
        self.ident = attrs["id"]
        # FIXME This is unused currently since we're using individual pages
        self.page_num = attrs["page_num"]
        self.confidence = attrs["confidence"]
        self.text = attrs["text"]
        self.x_min, self.y_min, self.x_max, self.y_max = self.get_bounds_from_attrs(attrs)
        self.children = []

    def set_children(self, children: List):
        self.children = children

    def get_bounds_from_attrs(self, attrs: List):
        bounds: str = attrs["bounds"][0]
        bounds: List = [int(b) for b in bounds.split(" ")[1:]]
        return bounds

    def get_bounds(self):
        # For standardization purposes
        return {
            "xmin": self.x_min / self.page_width * 1000,
            "ymin": self.y_min / self.page_height * 1000,
            "xmax": self.x_max / self.page_width * 1000,
            "ymax": self.y_max / self.page_height * 1000
        }

    def get_words(self):
        '''
        Specific to getting words within the block
        '''
        words: List = []
        def helper(el: Tess):
            if el.t_type == "ocrx_word":
                words.append(el)
            else:
                for child in el.children:
                    helper(child)
        helper(self)
        return words


class Abby:

    def __init__(self, attrs: Dict, a_type: AbbyType):
        self.a_type = a_type
        self.attrs = attrs
        self.children = []
        self.has_bounds = False
        self.parse_attrs()

    def parse_attrs(self):
        if self.a_type == AbbyType.CHAR:
            self.text = self.attrs["text"]

        if self.a_type == AbbyType.LINE or \
           self.a_type == AbbyType.WORD or \
           self.a_type == AbbyType.TABLE or \
           self.a_type == AbbyType.T_ROW:
            pass # Internal constructs or no direct attrs
        elif self.a_type == AbbyType.PAGE:
            self.page_num = int(self.attrs["page"])
            self.page_width = int(self.attrs["width"])
            self.page_height = int(self.attrs["height"])
        elif self.a_type == AbbyType.CHAR or self.a_type == AbbyType.P:
            try:
                self.l = int(self.attrs["l"])
                self.r = int(self.attrs["r"])
                self.t = int(self.attrs["t"])
                self.b = int(self.attrs["b"])
                self.has_bounds = True
            except:
                pass # textblock within tables are without coordinates
        else:
            raise("UNKNOWN TYPE for construction")

    def pass_page_dim(self, page_width, page_height):
        '''
        Pass page dimensions downward
        '''
        self.page_width = page_width
        self.page_height = page_height
        for child in self.children:
            child.pass_page_dim(page_width, page_height)

    def process(self) -> Tuple:
        '''
        Ensure every Abby object has bounds
        Ensure words have text field
        '''
        if not self.has_bounds:
            self.l, self.t, self.r, self.b = self.page_width, self.page_height, 0, 0
        for child in self.children:
            child.process()
            if not self.has_bounds:
                self.l = min(self.l, child.l)
                self.t = min(self.t, child.t)
                self.r = max(self.r, child.r)
                self.b = max(self.b, child.b)

        if self.a_type == AbbyType.WORD:
            self.text = "".join([char.text for char in self.children])

    def add_child(self, child: BeautifulSoup):
        self.children.append(child)

    def get_bounds(self):
        # For standardization purposes
        return {
            "xmin": self.l / self.page_width * 1000,
            "ymin": self.t / self.page_height * 1000,
            "xmax": self.r / self.page_width * 1000,
            "ymax": self.b / self.page_width * 1000
        }

    def get_words(self):
        '''
        Specific to getting words within the block
        '''
        words: List = []
        def helper(el: Abby):
            if el.a_type == AbbyType.WORD:
                words.append(el)
            else:
                for child in el.children:
                    helper(child)
        helper(self)
        return words



class Map:
    def __init__(self):
        return

    def compare(self, a_doc: List[Abby], t_doc: List[Tess]):
        # Pair pages for abby and tess
        paired = zip(a_doc, t_doc)
        for (abby_page, tess_page) in paired:
            # Test page 1
            self.get_page_info(abby_page, tess_page)
            break # TODO DELETE THIS

    def get_page_info(self, a_page: Abby, t_page: Tess):
        print("++++++++++++++++ NEW PAGE +++++++++++++++++++++")
        for child in t_page.children:
            t_words = child.get_words()
            overlapping = filter(lambda block: self.overlap(block, child), a_page.children)
            for o in overlapping: # Get overlapping regions from abby
                a_words = o.get_words()
                self.pair_words(a_words, t_words)
            # break # TODO DELETE THIS


    def pair_words(self, a_words: List[Abby], t_words: List[Tess]):
        print(" ====== PAIRING ======")
        paired = defaultdict(lambda: [])

        for t_word in t_words:
            for a_word in a_words:
                if self.overlap(a_word, t_word):
                    paired[t_word].append(a_word)

        for t_word, a_word in paired.items():
            # print(t_word.get_bounds())
            print(t_word.text, end=": ")
            # print(t_word.get_bounds())
            for word in a_word:
                print(word.text, end=", ")
                # print(word.get_bounds())
            print()


    def get_word_IOU(self, a_word: Abby, t_word: Tess):
        return
    def get_IOU(self, boxA: List, boxB: List):

        # determine the (x, y)-coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        # compute the area of intersection rectangle
        interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)

        # compute the area of both the prediction and ground-truth
        # rectangles
        boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
        boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)

        # compute the intersection over union by taking the intersection
        # area and dividing it by the sum of prediction + ground-truth
        # areas - the interesection area
        iou = interArea / float(boxAArea + boxBArea - interArea)

        # return the intersection over union value
        return iou


    def overlap(self, b1: Abby, b2: Tess):
        def overlap_1d(bounds1: Dict, bounds2: Dict):
            return bounds1["xmax"] >= bounds2["xmin"] and bounds2["xmax"] >= bounds1["xmin"]

        abby_bounds = b1.get_bounds()
        tess_bounds = b2.get_bounds()

        x_overlap = overlap_1d(
            {"xmin": abby_bounds["xmin"], "xmax": abby_bounds["xmax"]},
            {"xmin": tess_bounds["xmin"], "xmax": tess_bounds["xmax"]})
        y_overlap = overlap_1d(
            {"xmin": abby_bounds["ymin"], "xmax": abby_bounds["ymax"]},
            {"xmin": tess_bounds["ymin"], "xmax": tess_bounds["ymax"]})

        return x_overlap and y_overlap




