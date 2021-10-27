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
        for path in collection:
            if os.path.isdir(path):
                obj = Helpers.initialize_and_store_tree_from_directory(path, destination)
                obj_data = TreeObjectData(path, Tree)
            else:
                with open(path, 'rb') as f:
                    obj = Blob(f.read())
                    obj_data = TreeObjectData(path, Blob)
                    CVSStorage.store_object(obj.get_hash().hex(), obj.serialize(), Blob, destination)
            tree.add_object(obj_data, obj.get_hash())

        return tree