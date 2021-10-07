import abc
import itertools
import os
from dataclasses import dataclass
import hashlib
import pickle


class CVSObject(abc.ABC):
    @abc.abstractmethod
    def get_hash(self) -> bytes:
        pass

    @abc.abstractmethod
    def serialize(self) -> bytes:
        pass

    @staticmethod
    @abc.abstractmethod
    def deserialize(content: bytes) -> "CVSObject":
        pass


class Blob(CVSObject):
    '''Blob is a file container'''
    def __init__(self, content: bytes):
        self.content = content

    def serialize(self) -> bytes:
        return self.content

    @staticmethod
    def deserialize(content: bytes) -> "Blob":
        return Blob(content)

    def get_hash(self) -> bytes:
        header = b'blob #\0'

        return hashlib.sha1(header + self.content).digest()


class Commit(CVSObject):
    '''Commit is reference to a top-level tree'''
    def __init__(self, tree: "Tree"):
        self.tree = tree
        self.parent_commit: Commit = self

    def derive_commit(self, tree: "Tree") -> "Commit":
        commit = Commit(tree)
        commit.parent_commit = self

        return commit

    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def deserialize(content: bytes) -> "Commit":
        return pickle.loads(content)

    def get_hash(self) -> bytes:
        header = b'commit #\0'

        return hashlib.sha1(header + self.tree.get_hash() + self.parent_commit.tree.get_hash()).digest()


class Tree(CVSObject):
    '''Tree is a collection of blobs and trees. Represents a folder'''
    def __init__(self):
        self.children: dict[TreeObjectData, bytes] = {}

    def add_object(self, data: "TreeObjectData", object_hash: bytes):
        self.children[data] = object_hash

    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def deserialize(content: bytes) -> "Tree":
        return pickle.loads(content)

    def get_hash(self) -> bytes:
        header = b'tree #\0'
        sha1_bytes = 20
        counter = 0
        total_bytes = bytearray(sha1_bytes * len(self.children))
        for object_hash in itertools.chain(self.children.values()):
            for j in object_hash:
                total_bytes[counter] = j
                counter += 1

        return hashlib.sha1(header + total_bytes).digest()

    @staticmethod
    def initialize_from_directory(directory: str) -> "Tree":
        '''Return a Tree object representing a directory'''
        tree = Tree()
        for file in os.listdir(directory):
            full_path = os.path.join(directory, file)
            if os.path.isdir(full_path):
                file_data = TreeObjectData(file, Tree)
                obj = Tree.initialize_from_directory(full_path)
            else:
                file_data = TreeObjectData(file, Blob)
                with open(full_path, 'rb') as f:
                    obj = Blob(f.read())

            tree.add_object(file_data, obj.get_hash())

        return tree


@dataclass(frozen=True)
class TreeObjectData:
    name: str
    object_type: type

