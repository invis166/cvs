import pytest
import os

from modules.cvs_objects import Blob, Tree, Commit, TreeObjectData
from modules.utils import *


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


@pytest.fixture()
def blob1():
    return Blob(b'blob1 content')


@pytest.fixture()
def blob2():
    return Blob(b'blob2 content')


@pytest.fixture()
def tree():
    return Tree()


def test_initialize_and_store_from_directory_restore_properly(tmpdir):
    os.mkdir(os.path.join(tmpdir, 'first_dir'))
    os.mkdir(os.path.join(tmpdir, 'second_dir'))
    with open(os.path.join(tmpdir, 'first_file'), 'wb') as f:
        f.write(b'first_content')
    with open(os.path.join(tmpdir, 'second_file'), 'wb') as f:
        f.write(b'second_content')
    with open(os.path.join(tmpdir, 'first_dir/third_file'), 'wb') as f:
        f.write(b'third_content')
    with open(os.path.join(tmpdir, 'second_dir/fourth_file'), 'wb') as f:
        f.write(b'fourth_content')

    os.mkdir(os.path.join(tmpdir, '../strg'))
    tree = initialize_and_store_tree_from_directory(tmpdir, os.path.join(tmpdir, '../strg'))