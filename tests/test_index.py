import os
import pytest
from shutil import rmtree
from functools import partial
from unittest.mock import patch

from modules.cvs import Index
from modules.cvs_objects import Tree, Commit, Blob, TreeObjectData


def create_files(files):
    for full_path in files:
        os.makedirs(os.path.dirname(full_path) + '/', exist_ok=True)
        with open(full_path, 'w'):
            pass


@pytest.fixture()
def index(tmpdir):
    return Index(tmpdir)


@pytest.fixture()
def files(tmpdir):
    _files = [
        '123.txt',
        'folder/123.txt',
        '321.txt',
        'folder/folder1/321.txt'
    ]

    return list(map(partial(os.path.join, tmpdir), _files))


@pytest.fixture()
def tree():
    return Tree()


@pytest.fixture()
def commit(tree):
    return Commit(tree)


def test_update_index_empty_directory(commit, index, tmpdir):
    index.update(commit)

    assert index.removed == {}
    assert index.modified == {}
    assert index.new == {}


def test_update_index_empty_commit(commit, index, files, tmpdir):
    create_files(files)
    index.update(commit)

    assert index.removed == {}
    assert index.modified == {}
    assert index.new == Tree.initialize_from_directory(tmpdir).children


def test_update_index_modified_files_not_in_folder(commit, index, files, tmpdir):
    create_files(files)
    commit.tree.children[TreeObjectData(files[0], Blob)] = b'wired hash'
    index.update(commit)

    assert index.removed == {}

    assert TreeObjectData(files[0], Blob) in index.modified
    assert len(index.modified) == 1

    from_dir = Tree.initialize_from_directory(tmpdir)
    del from_dir.children[TreeObjectData(files[0], Blob)]
    assert index.new == from_dir.children


def test_update_index_modified_files_in_folder(commit, index, files, tmpdir):
    create_files(files)

    modified_tree = Tree.initialize_from_directory(os.path.dirname(files[1]))
    modified_tree.children[TreeObjectData(files[1], Blob)] = b'wired hash'
    del modified_tree.children[TreeObjectData(os.path.dirname(files[3]), Tree)]

    commit.tree.children = {TreeObjectData(os.path.dirname(files[1]), Tree): modified_tree.get_hash()}
    with patch('modules.cvs_objects.Tree.deserialize') as deserialize_patch:
        with patch('modules.storage.CVSStorage.read_object', side_effect=lambda *args: ''):
            deserialize_patch.return_value = modified_tree
            index.update(commit)

    assert index.removed == {}

    assert TreeObjectData(files[1], Blob) in index.modified
    assert len(index.modified) == 1

    from_dir = Tree.initialize_from_directory(tmpdir)
    from_dir_1 = Tree.initialize_from_directory(os.path.dirname(files[1]))
    new_expected = {
        TreeObjectData(files[0], Blob): from_dir.children[TreeObjectData(files[0], Blob)],
        TreeObjectData(files[2], Blob): from_dir.children[TreeObjectData(files[0], Blob)],
        TreeObjectData(os.path.dirname(files[3]), Tree): from_dir_1.children[TreeObjectData(os.path.dirname(files[3]), Tree)]
    }
    assert index.new == new_expected


def test_update_index_modified_whole_folder(commit, index, files, tmpdir):
    create_files(files)

    modified_tree = Tree.initialize_from_directory(os.path.dirname(files[1]))
    modified_tree.children[TreeObjectData(files[1], Blob)] = b'wired hash'
    other_modified_tree = Tree.initialize_from_directory(os.path.dirname(files[3]))
    other_modified_tree.children[TreeObjectData(files[3], Blob)] = b'other wired hash'
    modified_tree.children[TreeObjectData(os.path.dirname(files[3]), Tree)] = other_modified_tree.get_hash()

    commit.tree.children = {TreeObjectData(os.path.dirname(files[1]), Tree): modified_tree.get_hash()}

    objects_map = {os.path.dirname(files[1]): modified_tree, os.path.dirname(files[3]): other_modified_tree}
    with patch('modules.cvs_objects.Tree.deserialize',
               side_effect=lambda arg: objects_map[arg]):
        with patch('modules.storage.CVSStorage.read_object', side_effect=lambda *args: args[2]):
            index.update(commit)

    assert index.removed == {}

    assert TreeObjectData(files[1], Blob) in index.modified \
           and TreeObjectData(files[3], Blob) in index.modified \
           and len(index.modified) == 2

    from_dir = Tree.initialize_from_directory(tmpdir)
    new_expected = {TreeObjectData(files[0], Blob): from_dir.children[TreeObjectData(files[0], Blob)],
                    TreeObjectData(files[2], Blob): from_dir.children[TreeObjectData(files[0], Blob)]}
    assert index.new == new_expected


def test_update_index_remove_file(commit, index, files, tmpdir):
    create_files(files)

    commit.tree = Tree.initialize_from_directory(tmpdir)
    os.remove(files[0])
    index.update(commit)

    assert TreeObjectData(files[0], Blob) in index.removed and len(index.removed) == 1


# def test_update_index_remove_directory(commit, index, files, tmpdir):
#     create_files(files)
#
#     commit.tree = Tree.initialize_from_directory(tmpdir)
#     rmtree(os.path.dirname(files[1]))
#     index.update(commit)
#
#     assert TreeObjectData(os.path.dirname(files[1]), Tree) in index.removed and len(index.removed) ==
