import abc
import os


class CVSObject(metaclass=abc.ABCMeta):
    def get_hash(self) -> bytes:
        pass

    def get_content(self) -> bytes:
        pass

    @staticmethod
    def initialize_from_reference(path_to_reference: str) -> "CVSObject":
        pass


class Blob(CVSObject):
    def __init__(self):
        self.hash_sum = 'some_hash'
        self.content = b'data'


class Commit(CVSObject):
    def __init__(self, tree: "Tree"):
        self.tree = tree
        self.parent_commit = None

    def derive_commit(self, tree: "Tree") -> "Commit":
        commit = Commit(tree)
        commit.parent_commit = self

        return commit

    @staticmethod
    def initialize_from_reference(path_to_reference: str) -> "Commit":
        pass


class Tree(CVSObject):
    def __init__(self):
        self.children = {}

    def add_item(self, item_hash: bytes, item_name: str, item_type: str):
        self.children[item_hash] = _TreeObjectData(item_name, item_type)


class _TreeObjectData:
    def __init__(self, name: str, object_type: str):
        self.name = name
        self.object_type = object_type


class Branch(CVSObject):
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
    def __init__(self, branch: Branch):
        self.branch = branch

    @staticmethod
    def initialize_from_reference(path_to_reference: str) -> "Head":
        pass
