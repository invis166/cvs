import itertools
import os
from dataclasses import dataclass

from modules.cvs_objects import Commit, Tree, Blob, TreeObjectData
from modules.helpers import Helpers
from modules.references import Branch, Head, Reference
from modules.storage import CVSStorage
from modules.folders_enum import FoldersEnum


class CVS:
    def __init__(self, path: str):
        self.index: Index = Index(path)
        self.head: Head = None
        self.branches: list[Branch] = []
        self.path_to_repository = path
        self.ignore: set[TreeObjectData] = {TreeObjectData(os.path.join(path, FoldersEnum.CVS_DATA), Tree)}
        self.index.ignore = self.ignore

        self._full_path_to_objects = os.path.join(path, FoldersEnum.OBJECTS)
        self._full_path_to_references = os.path.join(path, FoldersEnum.REFS)

    def initialize_repository(self):
        if CVS.is_repository_exists(self.path_to_repository):
            # initializing refs
            self._initialize_head()
            self.index.update(self._initialize_commit_from_head())
            return

        # Creating internal files and directories
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))
        os.mkdir(self._full_path_to_objects)
        os.mkdir(self._full_path_to_references)
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.TAGS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.HEADS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.INDEX))
        with open(os.path.join(self.path_to_repository, FoldersEnum.HEAD), 'w'):
            pass

        commit = Commit(Tree())
        CVSStorage.store_object(commit.get_hash().hex(),
                                commit.serialize(),
                                Commit,
                                self._full_path_to_objects)
        branch = Branch('master', commit)
        CVSStorage.store_object(branch.name,
                                branch.get_pointer().hex().encode(),
                                Branch,
                                os.path.join(self.path_to_repository, FoldersEnum.HEADS))
        self.head = Head(branch)
        CVSStorage.store_object('HEAD',
                                self.head.get_pointer(),
                                Head,
                                os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))
        self.index.update(commit)

    def add_to_staged(self, path: str):
        if os.path.isdir(path):
            item = TreeObjectData(path, Tree)
        else:
            item = TreeObjectData(path, Blob)
        if item not in self.index.new and item not in self.index.modified and item not in self.index.removed \
                or item in self.ignore or item in self.index.staged:
            return

        self.index.staged.add(item)

    def make_commit(self):
        if not self.index.staged:
            return

        # make commit from staged files and store it
        commit_tree = Helpers.initialize_and_store_tree_from_collection(self.index.staged, self._full_path_to_objects)
        new_commit = Commit.derive_commit(self._initialize_commit_from_head(), commit_tree)
        CVSStorage.store_object(new_commit.get_hash().hex(), new_commit.serialize(), Commit, self._full_path_to_objects)

        # move head and branch to new commit and store them
        head, branch = self._move_head_to_commit(new_commit)
        if branch:
            CVSStorage.store_object(branch.name,
                                    branch.get_pointer().hex().encode(),
                                    Branch,
                                    os.path.join(self.path_to_repository, FoldersEnum.HEADS))
        CVSStorage.store_object('HEAD',
                                self.head.get_pointer(),
                                Head,
                                os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))

        self.index.staged = set()

    @staticmethod
    def is_repository_exists(path_to_repository: str) -> bool:
        path_to_cvs_data = os.path.join(path_to_repository, FoldersEnum.CVS_DATA)

        return os.path.isdir(path_to_cvs_data)

    def _move_head_to_commit(self, commit: Commit) -> tuple:
        if self.head.is_point_to_branch:
            new_branch = Branch(self.head.branch.name, commit)
            return Head(new_branch), new_branch
        else:
            return Head(commit), None

    def _initialize_head(self):
        self.head = Head(self._initialize_commit_from_head())

    def _initialize_commit_from_head(self) -> Commit:
        head = CVSStorage.read_object('HEAD',
                                       Reference,
                                       os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))
        if head.decode().startswith('ref'):
            branch_name = os.path.basename(head.decode())
            commit_hash = CVSStorage.read_object(
                branch_name, Branch, os.path.join(self.path_to_repository, FoldersEnum.HEADS))
            raw_commit = CVSStorage.read_object(commit_hash.decode(), Commit, self._full_path_to_objects)
        else:
            raw_commit = CVSStorage.read_object(head.decode(), Commit, self._full_path_to_objects)

        return Commit.deserialize(raw_commit)


class Index:
    def __init__(self, directory: str):
        self.directory = directory
        self.ignore: set[TreeObjectData] = set()
        self.staged: set[TreeObjectData] = set()
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
                        second.children[first_tree_object_data].hex(),
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

    def update(self, commit: "Commit"):
        comp_res = Index.compare_trees(Tree.initialize_from_directory(self.directory), commit.tree)
        not_in_ignore = lambda x: x not in self.ignore
        self.new = set(filter(not_in_ignore, comp_res.in_first))
        self.removed = set(filter(not_in_ignore, comp_res.in_second))
        self.modified = set(filter(not_in_ignore, comp_res.different))


@dataclass
class TreeComparisonResult:
    in_first: dict["TreeObjectData", bytes]
    in_second: dict["TreeObjectData", bytes]
    different: dict["TreeObjectData", bytes]

    def extend(self, other: "TreeComparisonResult"):
        self.in_first.update(other.in_first)
        self.in_second.update(other.in_second)
        self.different.update(other.different)
