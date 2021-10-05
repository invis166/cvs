import os
import abc

from cvs_objects import CVSObject


class KVStorage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def store(self, item):
        pass

    @abc.abstractmethod
    def read(self, data):
        pass


class FolderStorage(KVStorage):
    def __init__(self, directory: str):
        self.directory = directory

    def store(self, item: CVSObject):
        item_hash = item.get_object_hash()
        object_name = item_hash.hex()[2:]

        object_directory = FolderStorage.get_object_directory(self.directory, item_hash)
        os.makedirs(object_directory)

        with open(os.path.join(object_directory, object_name), 'wb') as f:
            f.write(item.serialize())

    def read(self, item_hash: bytes) -> bytes:
        object_name = item_hash.hex()[2:]
        object_directory = FolderStorage.get_object_directory(self.directory, item_hash)

        return FolderStorage.get_file_content(os.path.join(object_directory, object_name))

    @staticmethod
    def get_object_directory(path_to_objects: str, object_hash: bytes) -> str:
        return os.path.join(path_to_objects, object_hash.hex()[:2])

    @staticmethod
    def get_file_content(path: str):
        with open(path, 'rb') as f:
            return f.read()



