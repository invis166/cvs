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


@pytest.mark.parametrize("objects", [
    [(TreeObjectData('123', Blob), b'123'), (TreeObjectData('456', Blob), b'456')],
    [(TreeObjectData('123', Tree), b'123'), (TreeObjectData('456', Tree), b'456')],
    [(TreeObjectData('123', Tree), b'123'), (TreeObjectData('456', Blob), b'456')]
])
def test_add_object_properly_add_object(tree, objects):
    for obj in objects:
        tree.add_object(*obj)

    assert len(tree.children) == len(objects)
    for obj in objects:
        assert tree.children[obj[0]] == obj[1]


def test_hash_properly_when_empty(tree):
    assert isinstance(tree.get_hash(), bytes)


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


@pytest.mark.parametrize("some_tree", [
    'tree',
    'tree_with_objects'
])
def test_serialize_and_deserialize_return_the_same_tree(some_tree, request):
    tree = request.getfixturevalue(some_tree)
    raw = tree.serialize()
    out = Tree.deserialize(raw)

    assert out.children == tree.children


def test_initialize_return_empty_tree_from_empty_directory(tree):
    raise NotImplementedError


def test_initialize_properly_from_non_empty_directory(tree):
    raise NotImplementedError

