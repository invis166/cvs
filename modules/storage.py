import os
import abc

import cvs_objects


class KVStorage(metaclass=abc.ABCMeta):
    @staticmethod
    @abc.abstractmethod
    def store(key, value, destination):
        pass

    @staticmethod
    @abc.abstractmethod
    def read(key, source):
        pass


class SimpleStorage(KVStorage):
    @staticmethod
    def store(key: str, value: bytes, destination: str):
        os.makedirs(destination)
        with open(os.path.join(destination, key), 'wb') as f:
            f.write(value)

    @staticmethod
    def read(key: str, source: str) -> bytes:
        return CVSStorage.get_file_content(os.path.join(source, key))

    @staticmethod
    def get_file_content(path: str) -> bytes:
        with open(path, 'rb') as f:
            return f.read()


# TODO: Visitor Pattern
class CVSStorage(SimpleStorage):
    @staticmethod
    def store_object(item, item_hash, destination: str):
        if isinstance(item, cvs_objects.CVSObject):
            object_name = item_hash.hex()[2:]
            object_directory = CVSStorage.get_object_directory(destination, item_hash)
            CVSStorage.store(object_name, item.serialize(), object_directory)
        else:
            raise NotImplementedError

    @staticmethod
    def read_object(item_hash: bytes, item_type: type, source: str) -> bytes:
        if issubclass(item_type, cvs_objects.CVSObject):
            # item_hash = item.get_hash()
            object_name = item_hash.hex()[2:]
            object_directory = CVSStorage.get_object_directory(source, item_hash)
            return CVSStorage.read(object_name, object_directory)
        else:
            raise NotImplementedError

    @staticmethod
    def get_object_directory(path_to_objects: str, object_hash: bytes) -> str:
        return os.path.join(path_to_objects, object_hash.hex()[:2])

    @staticmethod
    def get_file_content(path: str):
        with open(path, 'rb') as f:
            return f.read()



