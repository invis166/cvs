import os
import abc

from modules.cvs_objects import CVSObject
from modules.references import Reference


class KVStorage(metaclass=abc.ABCMeta):
    @staticmethod
    @abc.abstractmethod
    def store(key, value, destination):
        pass

    @staticmethod
    @abc.abstractmethod
    def read(key, source):
        pass


class FolderStorage(KVStorage):
    @staticmethod
    def store(key: str, value: bytes, destination: str):
        os.makedirs(destination + '/', exist_ok=True)
        with open(os.path.join(destination, key), 'wb') as f:
            f.write(value)

    @staticmethod
    def read(key: str, source: str) -> bytes:
        return CVSStorage.get_file_content(os.path.join(source, key))

    @staticmethod
    def get_file_content(path: str) -> bytes:
        with open(path, 'rb') as f:
            return f.read()


# Visitor pattern
class CVSStorage(FolderStorage):
    @staticmethod
    def store_object(name: str, content: bytes, obj_type: type, destination: str):
        if issubclass(obj_type, CVSObject):
            truncated_name = name[2:]
            item_directory = CVSStorage.get_object_directory(destination, name)
            CVSStorage.store(truncated_name, content, item_directory)
        elif issubclass(obj_type, Reference):
            CVSStorage.store(name, content, destination)
        else:
            raise NotImplementedError

    @staticmethod
    def read_object(name: str, obj_type: type, source: str) -> bytes:
        if issubclass(obj_type, CVSObject):
            truncated_name = name[2:]
            item_directory = CVSStorage.get_object_directory(source, name)
            return CVSStorage.read(truncated_name, item_directory)
        elif issubclass(obj_type, Reference):
            content = CVSStorage.read(name, source)

            return content
        else:
            raise NotImplementedError

    @staticmethod
    def get_object_directory(path_to_objects: str, name: str) -> str:
        return os.path.join(path_to_objects, name[:2])

    @staticmethod
    def get_file_content(path: str):
        with open(path, 'rb') as f:
            return f.read()
