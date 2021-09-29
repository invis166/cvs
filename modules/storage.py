import os

from folders_enum import FoldersEnum
from cvs_objects import CVSObject


class KVStorage:
    def __init__(self, directory: str):
        self.directory = directory
        self.path_to_objects = os.path.join(self.directory, FoldersEnum.OBJECTS)

    def store(self, item: CVSObject):
        item_hash = item.get_hash()
        object_name = item_hash.hex()[2:]

        object_directory = KVStorage.get_object_directory(self.path_to_objects, item_hash)
        os.makedirs(object_directory)

        with open(os.path.join(object_directory, object_name), 'wb') as f:
            f.write(item.get_content())

    def read_from_hash(self, item_hash: bytes) -> bytes:
        object_name = item_hash.hex()[2:]

        object_directory = KVStorage.get_object_directory(self.path_to_objects, item_hash)
        with open(os.path.join(object_directory, object_name), 'rb') as f:
            return f.read()

    @staticmethod
    def get_object_directory(path_to_objects: str, object_hash: bytes) -> str:
        return os.path.join(path_to_objects, object_hash.hex()[:2])

