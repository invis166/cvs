import os
from dataclasses import dataclass

from modules.cvs_objects import CVSObject, Commit, Tree, Blob, TreeObjectData
from modules.references import Branch, Head
from modules.storage import CVSStorage
from modules.folders_enum import FoldersEnum


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
            self.index.update_index()
            return

        # Creating internal files and directories
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.OBJECTS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.REFS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.HEADS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.INDEX))
        with open(os.path.join(self.path_to_repository, 'HEAD'), 'w'):
            pass

        self.index.update_index()

    @staticmethod
    def is_repository_exists(path_to_repository: str) -> bool:
        path_to_cvs_data = os.path.join(path_to_repository, FoldersEnum.CVS_DATA)
        return os.path.isdir(path_to_cvs_data)

    def _initialize_head(self):
        path_to_cvs_data = os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA)
        self.head = CVSStorage.read('HEAD', path_to_cvs_data)


class Index:
    def __init__(self, directory: str):
        self.directory = directory
        self.modified: dict[TreeObjectData, bytes] = {}
        self.removed: dict[TreeObjectData, bytes] = {}
        self.new: dict[TreeObjectData, bytes] = {}

    @staticmethod
    def compare_trees(first: Tree, second: Tree) -> "TreeComparisonResult":
        in_first: dict[TreeObjectData, bytes] = {}
        in_second: dict[TreeObjectData, bytes] = {}
        different: dict[TreeObjectData, bytes] = {}
        res = TreeComparisonResult(in_first, in_second, different)

        equal: dict[TreeObjectData, bytes] = {}
        second_tree_objects_data = second.children.keys()
        for first_tree_object_data in first.children:
            if first_tree_object_data not in second_tree_objects_data:
                # current object is new
                in_first[first_tree_object_data] = first.children[first_tree_object_data]
            elif first.children[first_tree_object_data] != second.children[first_tree_object_data]:
                # current object was changed
                if first_tree_object_data.object_type == Tree:
                    first_subtree = Tree.initialize_from_directory(first_tree_object_data.path)
                    second_subtree = Tree.deserialize(CVSStorage.read_object(
                        second.children[first_tree_object_data],
                        Tree,
                        first_tree_object_data.path))
                    comp_res = Index.compare_trees(first_subtree, second_subtree)
                    res.extend(comp_res)
                elif first_tree_object_data.object_type == Blob:
                    different[first_tree_object_data] = first.children[first_tree_object_data]
                else:
                    equal[first_tree_object_data] = first.children[first_tree_object_data]
        in_second.update(map(lambda data: (data, second.children[data]),
                             filter(lambda data: data not in first.children, second.children)))

        return res

    def update_index(self, commit: "Commit"):
        comp_res = Index.compare_trees(Tree.initialize_from_directory(self.directory), commit.tree)
        self.new = comp_res.in_first
        self.removed = comp_res.in_second
        self.modified = comp_res.different

    @staticmethod
    def _enumerate_directory(directory: str) -> str:
        for file in os.listdir(directory):
            full_path = os.path.join(directory, file)
            if os.path.isdir(full_path):
                yield from Index._enumerate_directory(full_path)
            else:
                yield full_path

    def _enumerate_tree(self, tree: Tree) -> (TreeObjectData, bytes):
        for obj_data in tree.children.keys():
            if obj_data.object_type == Tree:
                other_tree = Tree.deserialize(CVSStorage.read_object(tree.children[obj_data], Tree, self.directory))
                yield from self._enumerate_tree(other_tree)
            else:
                yield obj_data, tree.children[obj_data]


@dataclass
class TreeComparisonResult:
    in_first: dict["TreeObjectData", bytes]
    in_second: dict["TreeObjectData", bytes]
    different: dict["TreeObjectData", bytes]

    def extend(self, other: "TreeComparisonResult"):
        self.in_first.update(other.in_first)
        self.in_second.update(other.in_second)
        self.different.update(other.different)

