import os
from cvs_objects import CVSObject, Commit, Tree, Blob, Branch, Head
from folders_enum import FoldersEnum


class CVS:
    def __init__(self, path: str):
        self.cvs_data_directory_name = FoldersEnum.CVS_DATA
        self.files_index: list[CVSObject] = []
        self.head: Head = None
        self.branches: list[Branch] = []
        self.path_to_repository = path

    def initialize_repository(self):
        path_to_data = os.path.join(self.path_to_repository, self.cvs_data_directory_name)
        if os.path.isdir(path_to_data):
            # Repository already exists
            return self._initialize_existing_repository()

        # Creating internal files and directories
        os.mkdir(os.path.join(path_to_data, FoldersEnum.OBJECTS))
        os.mkdir(os.path.join(path_to_data, FoldersEnum.REFS))
        os.mkdir(os.path.join(path_to_data, FoldersEnum.HEADS))
        with open(os.path.join(path_to_data, 'HEAD'), 'w'):
            pass

    def update_index(self):
        pass

    @staticmethod
    def is_repository_exists(path_to_repository: str) -> bool:
        path_to_cvs_data = os.path.join(path_to_repository, FoldersEnum.CVS_DATA)
        return os.path.isdir(path_to_cvs_data)

    def _initialize_existing_repository(self):
        # Initializing head
        self.head = Head.initialize_from_reference(os.path.join(self.path_to_repository,
                                                                self.cvs_data_directory_name,
                                                                'HEAD'))

        # Initializing branches (don't know for what)
        # path_to_heads = os.path.join(self.path_to_repository,
        #                              self.cvs_data_directory_name,
        #                              'refs/heads')
        # for branch in os.listdir(path_to_heads):
        #     path_to_branch = os.path.join(path_to_heads, branch)
        #     self.branches.append(Branch.initialize_from_reference(path_to_branch))



