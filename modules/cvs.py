import itertools
import os
from dataclasses import dataclass

from modules.cvs_objects import Commit, Tree, Blob, TreeObjectData
from modules.helpers import Helpers
from modules.references import Branch, Head, Reference, Tag
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
            self._initialize_head()
            self.update_index()
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

        # initialize commit and head and store them
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

        self.update_index()

    def add_to_staged(self, data: TreeObjectData):
        if data not in self.index.new and data not in self.index.modified and data not in self.index.removed \
                or data in self.ignore or data in self.index.staged:
            return

        self.index.staged.add(data)

    def make_commit(self):
        if not self.index.staged:
            return

        # make commit from staged files and store it
        commit_tree = Helpers.initialize_and_store_tree_from_collection(self.index.staged, self._full_path_to_objects)
        new_commit = Commit.derive_commit(self.get_commit_from_head(), commit_tree)
        CVSStorage.store_object(new_commit.get_hash().hex(), new_commit.serialize(), Commit, self._full_path_to_objects)

        # move head and branch to new commit and store them
        self.head = self.move_head_with_branch_to_commit(new_commit)
        self.store_head()
        if self.head.is_point_to_branch:
            self.store_branch(self.head.branch)

        self.index.staged = set()

    def get_full_tree_state(self, commit: Commit) -> Tree:
        full_tree = Tree()
        full_tree.children = commit.tree.children.copy()
        removed = set(filter(lambda x: x.is_removed, commit.tree.children))
        current_commit = commit
        while current_commit.parent_commit_hash != b'':
            prev_commit = Commit.deserialize(CVSStorage.read_object(current_commit.parent_commit_hash.hex(), Commit, self._full_path_to_objects))
            for item in prev_commit.tree.children:
                item_with_is_removed = TreeObjectData(item.path, item.object_type, is_removed=True)
                item_without_is_removed = TreeObjectData(item.path, item.object_type, is_removed=False)
                if item_with_is_removed in removed:
                    continue
                elif item_without_is_removed in full_tree.children:
                    continue

                if item.is_removed:
                    removed.add(item)
                full_tree.children[item] = prev_commit.tree.children[item]
            current_commit = prev_commit

        return full_tree

    def update_index(self):
        head_commit = self.get_commit_from_head()
        self.index.update(self.get_full_tree_state(head_commit))

    def get_commit_by_hash(self, commit_hash: str) -> Commit:
        raw_commit = CVSStorage.read_object(commit_hash, Commit, self._full_path_to_objects)

        return Commit.deserialize(raw_commit)

    def get_branch_by_name(self, branch_name: str) -> Branch:
        commit_hash = CVSStorage.read_object(branch_name,
                                            Branch,
                                            os.path.join(self.path_to_repository, FoldersEnum.HEADS))

        return Branch(branch_name, Commit.deserialize(commit_hash))

    def move_head_with_branch_to_commit(self, commit: Commit) -> Head:
        if self.head.is_point_to_branch:
            new_branch = Branch(self.head.branch.name, commit)
            return Head(new_branch)
        else:
            return Head(commit)

    def create_tag(self, tag_name: str):
        current_commit = self.get_commit_from_head()
        tag = Tag(tag_name, current_commit)
        CVSStorage.store_object(tag_name,
                                tag.get_pointer().hex().encode(),
                                Tag,
                                os.path.join(self.path_to_repository, FoldersEnum.TAGS))

    def delete_tag(self, tag_name: str):
        path_to_tag = os.path.join(self.path_to_repository, FoldersEnum.TAGS, tag_name)
        os.remove(path_to_tag)

    def store_head(self):
        CVSStorage.store_object('HEAD',
                                self.head.get_pointer(),
                                Head,
                                os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))

    def store_branch(self, branch: Branch):
        CVSStorage.store_object(branch.name,
                                branch.get_pointer().hex().encode(),
                                Branch,
                                os.path.join(self.path_to_repository, FoldersEnum.HEADS))

    @staticmethod
    def is_repository_exists(path_to_repository: str) -> bool:
        path_to_cvs_data = os.path.join(path_to_repository, FoldersEnum.CVS_DATA)

        return os.path.isdir(path_to_cvs_data)

    def _initialize_head(self):
        item = self._get_head_reference()
        self.head = Head(item)

    def get_commit_from_head(self) -> Commit:
        item = self._get_head_reference()
        if isinstance(item, Commit):
            return item
        else:
            return item.commit

    def _get_head_reference(self):
        head_reference = CVSStorage.read_object('HEAD',
                                                Reference,
                                                os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))
        if head_reference.decode().startswith('ref'):
            branch_name = os.path.basename(head_reference.decode())
            commit_hash = CVSStorage.read_object(
                branch_name, Branch, os.path.join(self.path_to_repository, FoldersEnum.HEADS))
            raw_commit = CVSStorage.read_object(commit_hash.decode(), Commit, self._full_path_to_objects)
            return Branch(branch_name, Commit.deserialize(raw_commit))
        else:
            raw_commit = CVSStorage.read_object(head_reference.decode(), Commit, self._full_path_to_objects)
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

    def update(self, tree: Tree):
        dir_tree = Tree.initialize_from_directory(self.directory)
        filtered_dir_tree = Tree()
        filtered_dir_tree.children = {k: v for k, v in dir_tree.children.items() if k not in self.ignore}

        comp_res = Index.compare_trees(filtered_dir_tree, tree)
        self.new = comp_res.in_first
        # если объект не найден и он помечен удаленным, то он нам не нужен
        self.removed = {TreeObjectData(data.path, data.object_type, is_removed=True): v
                        for data, v in comp_res.in_second.items()
                        if TreeObjectData(data.path, data.object_type, is_removed=True) not in tree.children}
        self.modified = comp_res.different


@dataclass
class TreeComparisonResult:
    in_first: dict["TreeObjectData", bytes]
    in_second: dict["TreeObjectData", bytes]
    different: dict["TreeObjectData", bytes]

    def extend(self, other: "TreeComparisonResult"):
        self.in_first.update(other.in_first)
        self.in_second.update(other.in_second)
        self.different.update(other.different)
