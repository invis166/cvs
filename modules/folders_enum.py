from enum import Enum


class FoldersEnum(str, Enum):
    CVS_DATA = '.cool_cvs/'
    REFS = 'refs/'
    HEADS = 'refs/heads'
    OBJECTS = 'objects/'
