import abc
import os
import hashlib


class CVSObject(abc.ABC):
    @abc.abstractmethod
    def get_object_hash(self) -> bytes:
        pass


class Blob(CVSObject):
    '''Blob is a file container'''
    def get_object_hash(self) -> bytes:
        header = f'blob #\0'.encode()

        return hashlib.sha1(header + self.content).digest()

    def __init__(self, content: bytes):
        self.content = content


class Commit(CVSObject):
    '''Commit is reference to a top-level tree'''
    def __init__(self, tree: "Tree"):
        self.tree = tree
        self.parent_commit: Commit = None

    def derive_commit(self, tree: "Tree") -> "Commit":
        commit = Commit(tree)
        commit.parent_commit = self

        return commit

    def get_object_hash(self) -> bytes:
        header = f'commit #\0'.encode()

        return hashlib.sha1(header + self.tree.get_object_hash() + self.parent_commit.tree.get_object_hash()).digest()


class Tree(CVSObject):
    '''Tree is a collection of blobs and trees. Represents a folder'''
    def __init__(self):
        self.children: dict[bytes, "_TreeObjectData"] = {}

    def add_object(self, obj: CVSObject, data: "_TreeObjectData"):
        self.children[obj.get_object_hash()] = data

    def get_object_hash(self) -> bytes:
        raise NotImplementedError

    @staticmethod
    def get_different_files(first: "Tree", second: "Tree") -> dict[bytes, "_TreeObjectData"]:
        first_tree_objects = set(first.children.items())
        second_tree_objects = set(second.children.items())

        return {obj_hash: obj_data
                for obj_hash, obj_data in first_tree_objects.symmetric_difference(second_tree_objects)}


class _TreeObjectData:
    def __init__(self, name: str, object_type: type):
        self.name = name
        self.type = object_type


class Branch(CVSObject):
    '''Branch is a reference to a commit'''
    def __init__(self, name: str, commit: Commit):
        self.name = name
        self.commit = commit

    def get_object_hash(self) -> bytes:
        pass


class Head(CVSObject):
    '''Head is a reference to a current branch'''
    def __init__(self, branch: Branch):
        self.branch = branch

    def get_object_hash(self) -> bytes:
        pass
