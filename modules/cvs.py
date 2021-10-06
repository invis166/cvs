import os
from dataclasses import dataclass

from cvs_objects import CVSObject, Commit, Tree, Blob, Branch, Head, TreeObjectData
from storage import CVSStorage
from folders_enum import FoldersEnum


class CVS:
    def __init__(self, path: str):
        self.index: Index = None
        self.head: Head = None
        self.storage = CVSStorage()
        self.branches: list[Branch] = []
        self.path_to_repository = path
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
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.INDEX))
        with open(os.path.join(self.path_to_repository, 'HEAD'), 'w'):
            pass

        self.update_index()

    def update_index(self):
        '''Compare current repository state to last commit and add new or changed or removed files to index'''
        pass

    @staticmethod
    def is_repository_exists(path_to_repository: str) -> bool:
        path_to_cvs_data = os.path.join(path_to_repository, FoldersEnum.CVS_DATA)
        return os.path.isdir(path_to_cvs_data)

    @staticmethod
    def enumerate_directory(directory: str) -> str:
        for file in os.listdir(directory):
            full_path = os.path.join(directory, file)
            if os.path.isdir(full_path):
                yield from CVS.enumerate_directory(full_path)
            else:
                yield file

    def _initialize_head(self):
        self.head = Head.initialize_from_reference(os.path.join(self.path_to_repository,
                                                                FoldersEnum.CVS_DATA,
                                                                'HEAD'))

class Index:
    def __init__(self, directory: str):
        self.tree = Tree.initialize_from_directory(directory)
        self.directory = directory
        self.modified: list[CVSObject] = []
        self.removed: list[CVSObject] = []

    def compare_trees(self, index_tree: "Tree", commit_tree: "Tree") -> "TreeComparisonResult":
        # берем все файлы из текущей дирректории и все файлы из последнего коммита
        # сравниваем все файлы текущей дирректории и все файлы из последнего коммита
        # для тех файлов, у которых совпадает хэш, сравниваем содержимое
        # если файл есть в текущей дирректории, но его нет в предыдущем коммите, значит он был добавлен
        # если файла нет в текуйщей дирректории, но он есть в последнем коммите, значит он был удален
        different: dict[TreeObjectData, bytes] = {}
        in_index: dict[TreeObjectData, bytes] = {}
        in_commit: dict[TreeObjectData, bytes] = {}
        res = TreeComparisonResult(in_index, in_commit, different)

        path_to_index = os.path.join(self.directory, FoldersEnum.INDEX)
        commit_objects_data = commit_tree.children.keys()
        for index_child_data in index_tree.children:
            if index_child_data not in commit_objects_data:
                # current is a new file
                in_index[index_child_data] = index_tree.children[index_child_data]
            elif index_tree.children[index_child_data] != commit_tree.children[index_child_data]:
                # current was changed
                if index_child_data.type == Tree:
                    index_subtree = CVSStorage.read_object(index_tree.children[index_child_data], Tree, path_to_index)
                    index_subtree = Tree.deserialize(index_subtree)
                    commit_subtree = CVSStorage.read_object(commit_tree.children[index_child_data], Tree, self.directory)
                    commit_subtree = Tree.deserialize(commit_subtree)
                    comp_result = self.compare_trees(index_subtree, commit_subtree)
                    res.extend(comp_result)
                else:
                    different[index_child_data] = index_tree.children[index_child_data]

        return TreeComparisonResult(in_index, in_commit, different)


@dataclass
class TreeComparisonResult:
    def __init__(self,
                 in_first: dict["TreeObjectData", bytes],
                 in_second: dict["TreeObjectData", bytes],
                 different: dict["TreeObjectData", bytes]):
        self.in_first = in_first
        self.in_second = in_second
        self.different = different

    def extend(self, other: "TreeComparisonResult"):
        self.in_first.update(other.in_first)
        self.in_second.update(other.in_second)
        self.different.update(other.different)

