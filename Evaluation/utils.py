from enum import IntEnum
from typing import Dict, List, Tuple, Callable

THRESHOLD = 0.3

class TessType(IntEnum):
    OCR_PAGE = 0
    OCR_AREA = 1
    OCR_PAR = 2
    OCR_LINE = 3 # OCR_CAPTION, OCR_HEADER, OCR_TEXTFLOAT are on the same indentation level
    OCRX_WORD = 4

class AbbyType(IntEnum):
    PAGE = 0
    TABLE = 1
    T_ROW = 2
    P = 3
    LINE = 4
    WORD = 5
    CHAR = 6
