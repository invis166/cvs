import os

from modules.cvs_objects import Tree, TreeObjectData, Blob
from modules.storage import CVSStorage


class Helpers:
    @staticmethod
    def initialize_and_store_tree_from_directory(directory: str, destination: str) -> Tree:
        '''Return a Tree object representing a directory'''
        tree = Tree()
        for file in os.listdir(directory):
            full_path = os.path.join(directory, file)
            if os.path.isdir(full_path):
                file_data = TreeObjectData(full_path, Tree)
                obj = Helpers.initialize_and_store_tree_from_directory(full_path, destination)
            else:
                file_data = TreeObjectData(full_path, Blob)
                with open(full_path, 'rb') as f:
                    obj = Blob(f.read())

            tree.add_object(file_data, obj.get_hash())
            CVSStorage.store_object(obj.get_hash().hex(), obj.serialize(), file_data.object_type, destination)

        return tree

    @staticmethod
    def initialize_and_store_tree_from_collection(collection, destination: str) -> Tree:
        tree = Tree()
        for data in collection:
            path = data.path
            if data.object_type == Tree:
                if not data.is_removed:
                    obj = Helpers.initialize_and_store_tree_from_directory(path, destination)
                    obj_data = TreeObjectData(path, Tree)
                else:
                    obj = Tree()
                    obj_data = TreeObjectData(path, Tree, is_removed=True)
            else:
                if not data.is_removed:
                    obj_data = TreeObjectData(path, Blob)
                    with open(path, 'rb') as f:
                        obj = Blob(f.read())
                        CVSStorage.store_object(obj.get_hash().hex(), obj.serialize(), Blob, destination)
                else:
                    obj = Blob(b'')
                    obj_data = TreeObjectData(path, Blob, is_removed=True)

            tree.add_object(obj_data, b'' if obj_data.is_removed else obj.get_hash())

        return tree

    @staticmethod
    def listdir_with_trailing_slash(directory: str):
        for item in os.listdir(directory):
            if os.path.isdir(item):
                yield os.path.join(item, '')
            else:
                yield item
