from editdistance import eval
from typing import Dict, List, Tuple, Callable
from bs4 import BeautifulSoup
from utils import TessType, AbbyType, THRESHOLD
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
            "ymax": self.b / self.page_height * 1000
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

    def get_page_info(self, a_page: Abby, t_page: Tess):
        assert(a_page.a_type == AbbyType.PAGE)
        print("++++++++++++++++ NEW PAGE +++++++++++++++++++++")

        all_paired = []

        for a_child in a_page.children:
            a_words = a_child.get_words()
            overlapping = filter(lambda block: self.overlap(block, a_child), t_page.children) # Overlapping Tesseract blocks
            for o in overlapping:
                t_words = o.get_words()
                all_paired.append(self.pair_words(a_words, t_words)) # Add Paired words within block

        # Calculations for each word
        total_words = 0
        total_words_considered = 0
        total_words_not_overlapping = 0
        iou_total = 0.0
        error_rate = 0.0
        for paired in all_paired:
            for a_word, t_word_stats in paired.items():
                total_words = total_words + 1
                t_word = t_word_stats[0]
                iou = t_word_stats[1]

                iou_total = iou_total + iou
                if iou > THRESHOLD: # Only consider character error rate for considered words > THRESHOLD
                    error_rate = error_rate + (eval(t_word.text, a_word.text) / len(a_word.text))
                    total_words_considered += 1
                    pass

                    # print("Abby Word: %s" % a_word.text, end=": ")
                    # print("Tesseract Word: %s (IOU: %s)" % (t_word.text, iou))
                else:
                    total_words_not_overlapping = total_words_not_overlapping + 1
                    pass
                    # print("IOU too low for Abby word: %s (IOU: %s)" % (a_word.text, iou))
                    # print("IOU too low for Tesseract word: %s (IOU: %s)" % (t_word.text, iou))
        print("TOTAL WORDS: %s" % (total_words))
        print("AVERAGE IOU : %s" % (iou_total / total_words))
        print("AVERAGE CHAR ERROR RATE : %s" % (error_rate / total_words_considered))
        print("TOTAL WORDS BELOW THRESHOLDING : %s" % (total_words_not_overlapping))


    def pair_words(self, a_words: List[Abby], t_words: List[Tess]):
        paired = defaultdict(lambda: []) # Potential pairing candidates
        # Get overlapping t_words for each a_word
        for a_word in a_words:
            for t_word in t_words:
                if self.overlap(a_word, t_word):
                    paired[a_word].append(t_word)

        single_paired = defaultdict(lambda: []) # Paired highest IOU
        for a_word, paired_t_words in paired.items():
            overlapping_word, iou = self.filter_word(a_word, paired_t_words)
            single_paired[a_word] = [overlapping_word, iou]

        return single_paired


    def filter_word(self, a_word: Abby, t_words: List[Tess]) -> Tess:
        '''
        Get word with highest IOU overlap
        '''
        a_word_bounds = [coord for coord in a_word.get_bounds().values()]

        current_highest_IOU = 0.0
        t_word_top: Tess = t_words[0] # Highest IOU overlap

        for t_word in t_words:
            t_word_bounds = [coord for coord in t_word.get_bounds().values()]
            iou = self.get_IOU(a_word_bounds, t_word_bounds)
            if iou > current_highest_IOU:
                current_highest_IOU = iou
                t_word_top = t_word
        return t_word_top, current_highest_IOU



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




