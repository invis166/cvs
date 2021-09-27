import abc


class CVSObject(metaclass=abc.ABCMeta):
    def get_hash(self) -> bytes:
        return b'hash'

    def get_content(self) -> bytes:
        return b'content'


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


class Tree(CVSObject):
    def __init__(self):
        self.children = {}

    def add_item(self, item_hash: bytes, item_name: str, item_type: str):
        self.children[item_hash] = TreeObjectData(item_name, item_type)


class TreeObjectData:
    def __init__(self, name: str, object_type: str):
        self.name = name
        self.object_type = object_type
