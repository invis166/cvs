import os

from cvs_objects import CVSObject, Commit, Tree, Blob, Branch, Head
from storage import KVStorage
from folders_enum import FoldersEnum


class CVS:
    def __init__(self, path: str):
        self.files_index: list[CVSObject] = []
        self.head: Head = None
        self.branches: list[Branch] = []
        self.path_to_repository = path
        self.storage = KVStorage(self.path_to_repository)
        self.initialize_repository()

    def initialize_repository(self):
        if CVS.is_repository_exists(self.path_to_repository):
            # Just initializing refs
            self._initialize_head()
            self.update_index()
            return

        # Creating internal files and directories
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.OBJECTS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.REFS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.HEADS))
        with open(os.path.join(self.path_to_repository, 'HEAD'), 'w'):
            pass

        self.update_index()

    def update_index(self):
        '''Compare current repository state to last commit and add new or changed or removed files to index'''
        for object_hash, object_data in self.head.branch.commit.tree:
            # обходим все файлы в репозитории, смотрим, есть ли они в предыдущем коммите
            # если есть, сравниваем содержимое
            pass

    @staticmethod
    def is_repository_exists(path_to_repository: str) -> bool:
        path_to_cvs_data = os.path.join(path_to_repository, FoldersEnum.CVS_DATA)
        return os.path.isdir(path_to_cvs_data)

    def _initialize_head(self):
        self.head = Head.initialize_from_reference(os.path.join(self.path_to_repository,
                                                                FoldersEnum.CVS_DATA,
                                                                'HEAD'))



