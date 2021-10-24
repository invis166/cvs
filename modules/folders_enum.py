from enum import Enum


class FoldersEnum(str, Enum):
    CVS_DATA_FOLDER_NAME = 'cool_cvs'

    CVS_DATA = f'{CVS_DATA_FOLDER_NAME}/'
    REFS = f'{CVS_DATA_FOLDER_NAME}/refs/'
    HEAD = f'{CVS_DATA_FOLDER_NAME}/HEAD'
    HEADS = f'{CVS_DATA_FOLDER_NAME}/refs/heads/'
    TAGS = f'{CVS_DATA_FOLDER_NAME}/refs/tags'
    OBJECTS = f'{CVS_DATA_FOLDER_NAME}/objects/'
    INDEX = f'{CVS_DATA_FOLDER_NAME}/index/'
