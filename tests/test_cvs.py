import pytest
import os

from modules.folders_enum import FoldersEnum
from modules.cvs import CVS
from modules.cvs_objects import Commit, TreeObjectData, Tree, Blob
from modules.references import Tag


@pytest.fixture()
def cvs(tmpdir):
    cvs = CVS(tmpdir)
    cvs.initialize_repository()

    return cvs


def create_tag(tag_name, cvs):
    tag_name = 'test_tag'
    cvs.create_tag(tag_name)

    return os.path.join(cvs.path_to_repository, FoldersEnum.TAGS, tag_name)


def test_create_tag(tmpdir, cvs):
    path_to_tag = create_tag('test_tag', cvs)

    with open(path_to_tag, 'rb') as f:
        assert f.read() == cvs.get_commit_from_head().get_hash().hex().encode()


def test_delete_existing_tag_doNotThrow(tmpdir, cvs):
    tag_name = 'test_tag'
    path_to_tag = create_tag(tag_name, cvs)

    cvs.delete_tag(tag_name)


def test_delete_existing_tag_removesDirectory(tmpdir, cvs):
    tag_name = 'test_tag'
    path_to_tag = create_tag(tag_name, cvs)

    cvs.delete_tag(tag_name)

    assert os.path.exists(path_to_tag) == False

def test_delete_non_existing_tag_thows(tmpdir, cvs):
    with pytest.raises(FileNotFoundError):
        cvs.delete_tag('do_not_exist')
