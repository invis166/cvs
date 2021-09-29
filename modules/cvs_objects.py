import abc
import os
import hashlib

from folders_enum import FoldersEnum


class CVSObject(metaclass=abc.ABCMeta):
    def get_hash(self) -> bytes:
        pass

    def get_content(self) -> bytes:
        pass

    @staticmethod
    def initialize_from_reference(path_to_reference: str) -> "CVSObject":
        pass


class Blob(CVSObject):
    '''Blob is a file container'''
    def __init__(self, content: bytes):
        self.content = content

    def get_hash(self) -> bytes:
        header = f'blob #\0'.encode()

        return hashlib.sha1(header + self.content).digest()


class Commit(CVSObject):
    '''Commit is reference to a top-level tree'''
    def __init__(self, tree: "Tree"):
        self.tree = tree
        self.parent_commit = None

    def derive_commit(self, tree: "Tree") -> "Commit":
        commit = Commit(tree)
        commit.parent_commit = self

        return commit

    def get_hash(self) -> bytes:
        header = f'commit #\0'.encode()

        return hashlib.sha1(header + self.tree.get_hash()).digest()

    @staticmethod
    def initialize_from_reference(path_to_reference: str) -> "Commit":
        pass


class Tree(CVSObject):
    '''Tree is a collection of blobs and trees. Representing folder'''
    def __init__(self):
        self.children: dict[bytes, _TreeObjectData] = {}

    def __iter__(self) -> "Tree":
        return self

    def __next__(self) -> tuple[bytes, "_TreeObjectData"]:
        for object_hash, object_data in self.children.items():
            return object_hash, object_data

    def get_hash(self) -> bytes:
        raise NotImplementedError

    def add_object(self, object_hash: bytes, object_name: str, object_type: type):
        self.children[object_hash] = _TreeObjectData(object_name, object_type)


class _TreeObjectData:
    def __init__(self, name: str, object_type: type):
        self.name = name
        self.object_type = object_type


class Branch(CVSObject):
    '''Branch is a reference to a commit'''
    def __init__(self, name: str, commit: Commit):
        self.name = name
        self.commit = commit

    @staticmethod
    def initialize_from_reference(path_to_reference: str) -> "Branch":
        branch_name = os.path.basename(path_to_reference)
        with open(path_to_reference, 'r') as ref:
            commit_ref_dir = ref.readline()[0][:5]  # removing 'ref: ' prefix

        return Branch(branch_name, Commit.initialize_from_reference(commit_ref_dir))


class Head(CVSObject):
    '''Head is a reference to a current branch'''
    def __init__(self, branch: Branch):
        self.branch = branch

    @staticmethod
    def initialize_from_reference(path_to_reference: str) -> "Head":
        pass
