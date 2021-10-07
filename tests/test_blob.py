import pytest

from modules.cvs_objects import Blob


@pytest.fixture()
def content():
    return b'content'


@pytest.fixture()
def blob(content):
    return Blob(content)


def test_properly_initialize(content):
    blob = Blob(content)

    assert blob.content == content


def test_serialize_and_deserialize_return_the_same_tree(blob):
    raw = blob.serialize()
    out = Blob.deserialize(raw)

    assert blob.content == out.content


def test_hash_properly_when_empty():
    assert Blob(b'').get_hash() is not None


def test_hash_do_not_change_on_same_object(blob):
    first = blob.get_hash()
    second = blob.get_hash()

    return first == second


def test_hash_different_with_different_blobs():
    first = Blob(b'first')
    second = Blob(b'second')

    return first.get_hash() != second.get_hash()
