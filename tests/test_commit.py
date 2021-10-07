import pytest

from modules.cvs_objects import Blob, Commit, Tree, TreeObjectData


@pytest.fixture()
def tree():
    return Tree()


@pytest.fixture()
def commit(tree):
    return Commit(tree)


def test_derive_commit_save_parent_commit(commit, tree):
    derived = commit.derive_commit(tree)

    assert derived.parent_commit == commit


def test_hash_properly_when_empty(commit):
    assert commit.get_hash() is not None


def test_hash_changes_when_elements_changes(commit, tree):
    objects = [
        [TreeObjectData('123', Blob), b'123'],
        [TreeObjectData('321', Tree), b'321'],
        [TreeObjectData('111', Blob), b'111']
    ]
    for obj in objects:
        tree.add_object(*obj)

    prev_hash = commit.get_hash()
    tree.children[TreeObjectData('123', Blob)] = b'changed'
    curr_hash = commit.get_hash()

    assert prev_hash != curr_hash


def test_hash_changes_when_add_objects(commit, tree):
    tree.add_object(TreeObjectData('123', Blob), b'123')
    prev_hash = commit.get_hash()
    tree.add_object(TreeObjectData('321', Tree), b'321')
    curr_hash = tree.get_hash()

    assert prev_hash != curr_hash



def test_derive_commit_save_tree_elements(commit, tree):
    objects = [
        [TreeObjectData('123', Blob), b'123'],
        [TreeObjectData('321', Tree), b'321'],
        [TreeObjectData('111', Blob), b'111']
    ]
    for obj in objects:
        tree.add_object(*obj)

    derived = commit.derive_commit(tree)

    for obj in objects:
        assert derived.tree.children[obj[0]] == obj[1]
