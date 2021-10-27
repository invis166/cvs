import pytest
import os

from modules.storage import CVSStorage
from modules.cvs_objects import Blob, Tree, Commit, TreeObjectData
from modules.references import Tag, Branch, Head


@pytest.fixture()
def blob1():
    return Blob(b'blob1 content')


@pytest.fixture()
def blob2():
    return Blob(b'blob2 content')


@pytest.fixture()
def tree():
    return Tree()


@pytest.fixture()
def tree_children(blob1, blob2, tmpdir):
    return {
        TreeObjectData(os.path.join(tmpdir, 'blob1'), Blob): blob1.get_hash(),
        TreeObjectData(os.path.join(tmpdir, 'blob2'), Blob): blob2.get_hash()
    }


@pytest.fixture()
def tree_with_children(tree_children):
    tree = Tree()
    tree.children = tree_children

    return tree


def test_store_and_read_blob(blob1, tmpdir):
    CVSStorage.store_object(blob1.get_hash().hex(), blob1.serialize(), Blob, tmpdir)

    from_disk = Blob.deserialize(CVSStorage.read_object(blob1.get_hash().hex(), Blob, tmpdir))

    assert from_disk.content == blob1.content


def test_store_and_read_tree_same_hash(tree_with_children, tmpdir):
    CVSStorage.store_object(tree_with_children.get_hash().hex(), tree_with_children.serialize(), Tree, tmpdir)

    from_disk = Tree.deserialize(CVSStorage.read_object(tree_with_children.get_hash().hex(), Tree, tmpdir))

    assert from_disk.get_hash() == tree_with_children.get_hash()


def test_store_and_read_tree_same_children(tree_with_children, tmpdir):
    CVSStorage.store_object(tree_with_children.get_hash().hex(), tree_with_children.serialize(), Tree, tmpdir)

    from_disk = Tree.deserialize(CVSStorage.read_object(tree_with_children.get_hash().hex(), Tree, tmpdir))

    assert from_disk.children == tree_with_children.children


def test_read_tree_blobsAfterStoreSameContent(tree_with_children, blob1, blob2, tmpdir):
    CVSStorage.store_object(blob1.get_hash().hex(), blob1.serialize(), Blob, tmpdir)
    CVSStorage.store_object(blob2.get_hash().hex(), blob2.serialize(), Blob, tmpdir)
    CVSStorage.store_object(tree_with_children.get_hash().hex(), tree_with_children.serialize(), Tree, tmpdir)

    tree_from_disk = Tree.deserialize(CVSStorage.read_object(tree_with_children.get_hash().hex(), Tree, tmpdir))
    blob1_from_disk = Blob.deserialize(CVSStorage.read_object(
        tree_from_disk.children[TreeObjectData(os.path.join(tmpdir, 'blob1'), Blob)].hex(),
        Blob,
        tmpdir
    ))
    blob2_from_disk = Blob.deserialize(CVSStorage.read_object(
        tree_from_disk.children[TreeObjectData(os.path.join(tmpdir, 'blob2'), Blob)].hex(),
        Blob,
        tmpdir
    ))

    assert blob1_from_disk.content == blob1.content
    assert blob2_from_disk.content == blob2.content



