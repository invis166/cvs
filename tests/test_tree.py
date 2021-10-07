import pytest

from modules.cvs_objects import Tree, Blob, TreeObjectData


def test_add_object_with_blobs():
    tree = Tree()
    objects = [(TreeObjectData('123', Blob), b'123'), (TreeObjectData('456', Blob), b'456')]
    tree.add_object(*objects[0])
    tree.add_object(*objects[1])

    assert len(tree.children) == 2
    for obj in objects:
        assert obj[0] in tree
        assert tree.children[obj[0]] == obj[1]
