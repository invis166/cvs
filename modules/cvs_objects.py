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
    def __init__(self, content: bytes, is_removed=False):
        self.content = content
        self.is_removed = is_removed

    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def deserialize(content: bytes) -> "Blob":
        return pickle.loads(content)

    def get_hash(self) -> bytes:
        header = b'blob #\0'

        return hashlib.sha1(header + self.content).digest()


class Commit(CVSObject):
    '''Commit is reference to a top-level tree'''
    def __init__(self, tree: "Tree", message=''):
        self.tree = tree
        self.parent_commit_hash: bytes = b''
        self.message = message

    def derive_commit(self, tree: "Tree") -> "Commit":
        commit = Commit(tree)
        commit.parent_commit_hash = self.get_hash()

        return commit

    def serialize(self) -> bytes:
        return pickle.dumps(self)

    @staticmethod
    def deserialize(content: bytes) -> "Commit":
        return pickle.loads(content)

    def get_hash(self) -> bytes:
        header = b'commit #\0'

        return hashlib.sha1(header + self.tree.get_hash() + self.parent_commit_hash).digest()


class Tree(CVSObject):
    '''Tree is a collection of blobs and trees'''
    def __init__(self, is_removed=False):
        self.children: dict[TreeObjectData, bytes] = {}
        self.is_removed = is_removed

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
                full_path = os.path.join(full_path, '')
                file_data = TreeObjectData(full_path, Tree)
                obj = Tree.initialize_from_directory(full_path)
            else:
                file_data = TreeObjectData(full_path, Blob)
                with open(full_path, 'rb') as f:
                    obj = Blob(f.read())

            tree.add_object(file_data, obj.get_hash())

        return tree


@dataclass(frozen=True)
class TreeObjectData:
    path: str
    object_type: type
    is_removed: bool = False

    @property
    def name(self) -> str:
        return os.path.basename(self.path)
