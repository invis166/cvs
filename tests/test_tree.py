import os
import pytest

from modules.cvs_objects import Tree, Blob, TreeObjectData


@pytest.fixture
def tree():
    return Tree()


@pytest.fixture
def tree_with_objects():
    tree = Tree()
    objects = [
        (TreeObjectData('123', Tree), b'123'),
        (TreeObjectData('456', Blob), b'456'),
        (TreeObjectData('777', Blob), b'777')
    ]

    for obj in objects:
        tree.add_object(obj[0], obj[1])

    return tree


@pytest.fixture
def objects():
    objects = [
        'first.obj',
        'second.obj',
        'third.obj'
    ]

    return objects


@pytest.mark.parametrize("tree_objects", [
    [(TreeObjectData('123', Blob), b'123'), (TreeObjectData('456', Blob), b'456')],
    [(TreeObjectData('123', Tree), b'123'), (TreeObjectData('456', Tree), b'456')],
    [(TreeObjectData('123', Tree), b'123'), (TreeObjectData('456', Blob), b'456')]
])
def test_add_object_properly_add_object(tree, tree_objects):
    for obj in tree_objects:
        tree.add_object(*obj)

    assert len(tree.children) == len(tree_objects)
    for obj in tree_objects:
        assert tree.children[obj[0]] == obj[1]


def test_hash_properly_when_empty(tree):
    assert tree.get_hash() is not None


def test_hash_do_not_change_on_same_object(tree):
    tree.add_object(TreeObjectData('123', Blob), b'123')
    first = tree.get_hash()
    second = tree.get_hash()

    assert first == second


def test_hash_changes_when_add_objects(tree):
    objects = [
        (TreeObjectData('123', Tree), b'123'),
        (TreeObjectData('456', Blob), b'456'),
        (TreeObjectData('777', Blob), b'777')
    ]

    prev_hash = tree.get_hash()
    for obj in objects:
        tree.add_object(obj[0], obj[1])
        assert tree.get_hash() != prev_hash
        prev_hash = tree.get_hash()


def test_hash_changes_when_elements_changes(tree_with_objects):
    prev_hash = tree_with_objects.get_hash()
    tree_with_objects.children[TreeObjectData('123', Tree)] = b'changed'
    curr_hash = tree_with_objects.get_hash()

    assert prev_hash != curr_hash


@pytest.mark.parametrize("some_tree", [
    'tree',
    'tree_with_objects'
])
def test_serialize_and_deserialize_return_the_same_tree(some_tree, request):
    tree = request.getfixturevalue(some_tree)
    raw = tree.serialize()
    out = Tree.deserialize(raw)

    assert out.children == tree.children


def test_initialize_return_empty_tree_from_empty_directory(tmpdir):
    tree = Tree.initialize_from_directory(tmpdir)

    assert len(tree.children) == 0


def test_initialize_save_file_content(tmpdir, objects):
    for obj in objects:
        full_path = os.path.join(tmpdir, obj)
        with open(full_path, 'wb') as f:
            f.write(obj.encode())

    tree = Tree.initialize_from_directory(tmpdir)
    for obj in objects:
        data = TreeObjectData(os.path.join(tmpdir, obj), Blob)
        assert tree.children[data] == Blob(obj.encode()).get_hash()


def test_initialize_save_subdirectories(tmpdir):
    subdirs = [
        'subdir1',
        'subdir2/subsubdir1/subsubdir2',
        'subdir3/subsubdir2'
        ]
    for subdir in subdirs:
        full_path = os.path.join(tmpdir, subdir)
        os.makedirs(full_path, exist_ok=True)

    tree = Tree.initialize_from_directory(tmpdir)
    for subdir in subdirs:
        full_path = os.path.join(tmpdir, subdir)
        data = TreeObjectData(os.path.join(tmpdir, subdir.split('/')[0], ''), Tree)
        sub_tree = build_tree_from_string(subdir)

        assert tree.children[data] == sub_tree.get_hash()


def build_tree_from_string(string: str):
    subfolders = string.split('/')
    if len(subfolders) == 1:
        if subfolders[0].split('.')[-1] == 'obj':
            return Blob(subfolders[0].encode())
        return Tree()

    tree = Tree()
    tree.add_object(TreeObjectData(subfolders[0], Tree), build_tree_from_string('/'.join(subfolders[1:])).get_hash())

    return tree
