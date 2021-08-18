import enum
from ._jntajis import IncrementalEncoder, encode, decode, shrink_translit


class ConversionMode(enum.IntEnum):
    SISO              = 0
    MEN1              = 1
    JISX0208          = 2
    JISX0208_TRANSLIT = 3

