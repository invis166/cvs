import abc

from cvs_objects import CVSObject, Commit
from folders_enum import FoldersEnum


class Reference(abc.ABC):
    @abc.abstractmethod
    def get_pointer(self) -> bytes:
        pass


class Branch(Reference):
    '''Branch is a reference to a commit'''
    def __init__(self, name: str, commit: Commit):
        self.name = name
        self.commit = commit

    def get_pointer(self) -> bytes:
        return self.commit.get_hash()


class Head(Reference):
    '''Head is a reference to a current branch'''
    def __init__(self, item):
        self.item = item
        self.is_point_to_branch = isinstance(item, Branch)
        if isinstance(item, Commit):
            self.content = item.get_hash()
            self.commit = item
        elif isinstance(item, Branch):
            self.content = f'ref: {FoldersEnum.REFS}{item.name}'.encode()
            self.branch = item

    def get_pointer(self) -> bytes:
        return self.content


class Tag(Reference):
    '''Tag is a reference to a commit, but it is not moving unlike Branch'''
    def __init__(self, name: str, commit: Commit):
        self.name = name
        self.commit = commit

    def get_pointer(self) -> bytes:
        return self.commit.get_hash()
