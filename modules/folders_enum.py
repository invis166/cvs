from enum import Enum


class FoldersEnum(str, Enum):
    CVS_DATA = '.cool_cvs/'
    REFS = '.cool_cvs/refs/'
    HEADS = '.cool_cvs/refs/heads'
    OBJECTS = '.cool_cvs/objects/'
    INDEX = '.cool_cvs/index/'
