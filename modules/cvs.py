import os.path
from dataclasses import dataclass

from modules.cvs_objects import Commit, Tree, Blob, TreeObjectData
from modules.utils import *
from modules.references import Branch, Head, Reference, Tag
from modules.storage import CVSStorage
from modules.folders_enum import FoldersEnum
from modules.rebase_state import RebaseState


class CVS:
    def __init__(self, path: str):
        self.index: Index = Index(path, self)
        self.head: Head = None
        self.branches: list[Branch] = []
        self.path_to_repository = path
        self.ignore: set[TreeObjectData] = {TreeObjectData(os.path.join(path, FoldersEnum.CVS_DATA), Tree)}
        self.index.ignore = self.ignore
        self.rebase_state: RebaseState = None

        self._full_path_to_objects = os.path.join(path, FoldersEnum.OBJECTS)
        self._full_path_to_references = os.path.join(path, FoldersEnum.REFS)

    def initialize_repository(self):
        if CVS.is_repository_exists(self.path_to_repository):
            self._initialize_head()
            self.update_index()
            return

        # Creating internal files and directories
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))
        os.mkdir(self._full_path_to_objects)
        os.mkdir(self._full_path_to_references)
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.TAGS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.HEADS))
        os.mkdir(os.path.join(self.path_to_repository, FoldersEnum.INDEX))
        with open(os.path.join(self.path_to_repository, FoldersEnum.HEAD), 'w'):
            pass

        # initialize commit and head and store them
        commit = Commit(Tree())
        CVSStorage.store_object(commit.get_hash().hex(),
                                commit.serialize(),
                                Commit,
                                self._full_path_to_objects)
        branch = Branch('master', commit)
        CVSStorage.store_object(branch.name,
                                branch.get_pointer().hex().encode(),
                                Branch,
                                os.path.join(self.path_to_repository, FoldersEnum.HEADS))
        self.head = Head(branch)
        CVSStorage.store_object('HEAD',
                                self.head.get_pointer(),
                                Head,
                                os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))

        self.update_index()

    def add_to_staged(self, data: TreeObjectData):
        if data not in self.index.new and data not in self.index.modified and data not in self.index.removed \
                or data in self.ignore or data in self.index.staged:
            return

        self.index.staged.add(data)

    def make_commit(self, message=''):
        if not self.index.staged:
            return

        # make commit from staged files and store it
        commit_tree = initialize_and_store_tree_from_collection(self.index.staged, self._full_path_to_objects)
        new_commit = Commit.derive_commit(self.get_commit_from_head(), commit_tree, message=message)
        CVSStorage.store_object(new_commit.get_hash().hex(), new_commit.serialize(), Commit, self._full_path_to_objects)

        # move head and branch to new commit and store them
        self.head = self.move_head_with_branch_to_commit(new_commit)
        self.store_head()
        if self.head.is_point_to_branch:
            self.store_branch(self.head.branch)

        self.index.staged = set()

    def expand_full_tree(self, commit: Commit) -> dict[TreeObjectData, bytes]:
        files = {}
        removed = set(filter(lambda x: x.is_removed, commit.tree.children))
        for parent in self.enumerate_commit_parents(commit, return_itself=True):
            for item, item_hash in parent.tree.children.items():
                blobs = []
                if item.object_type is Tree:
                    tree = Tree.deserialize(CVSStorage.read_object(item_hash.hex(), Tree, self._full_path_to_objects))
                    for pair in self.enumerate_tree_files(tree):
                        blobs.append(pair)
                else:
                    blobs.append((item, item_hash))

                for blob, blob_hash in blobs:
                    item_with_is_removed = TreeObjectData(blob.path, blob.object_type, is_removed=True)
                    item_without_is_removed = TreeObjectData(blob.path, blob.object_type, is_removed=False)
                    if item_with_is_removed in removed:
                        continue
                    elif item_without_is_removed in files:
                        continue

                    if blob.is_removed:
                        removed.add(blob)
                    files[blob] = blob_hash

        return files

    def get_full_tree_state(self, commit: Commit) -> Tree:
        full_tree = Tree()
        full_tree.children = commit.tree.children.copy()
        removed = set(filter(lambda x: x.is_removed, commit.tree.children))
        for parent in self.enumerate_commit_parents(commit):
            for item in parent.tree.children:
                item_with_is_removed = TreeObjectData(item.path, item.object_type, is_removed=True)
                item_without_is_removed = TreeObjectData(item.path, item.object_type, is_removed=False)
                if item_with_is_removed in removed:
                    continue
                elif item_without_is_removed in full_tree.children:
                    continue

                if item.is_removed:
                    removed.add(item)
                full_tree.children[item] = parent.tree.children[item]

        return full_tree

    def update_index(self):
        head_commit = self.get_commit_from_head()
        self.index.update(head_commit)

    def initialize_rebase_state(self, src_branch: Branch):
        head_branch = self.get_branch_from_head()
        head_commit = head_branch.commit
        head_commit_parents = {parent for parent in self.enumerate_commit_parents(head_commit, return_itself=True)}
        self.rebase_state = RebaseState(src_branch, head_branch)

        common_commit = None
        for branch_parent in self.enumerate_commit_parents(src_branch.commit, return_itself=True):
            if branch_parent in head_commit_parents:
                common_commit = branch_parent
                break
            self.rebase_state.not_applied.append(branch_parent)
        if common_commit is None:
            common_commit = Commit(Tree())

        for head_parent in self.enumerate_commit_parents(head_commit, return_itself=True):
            for item in head_parent.tree.children:
                self.rebase_state.destination_branch_changed.add(item)
            if head_parent == common_commit:
                break

        self.rebase_state.current_dst_commit = head_commit

    def continue_rebase(self) -> RebaseState:
        if not self.rebase_state or not self.rebase_state.is_conflict:
            raise ValueError('not in rebase')
        self.rebase_state.is_conflict = False

        state = self.rebase()
        self.make_commit('resolve rebase conflict')
        if state.is_conflict:
            state.current_dst_commit = self.head.branch.commit

        return state

    def abort_rebase(self):
        if not self.rebase_state:
            return
        # передвигаем head и branch в начальное положение
        self.head = self.move_head_with_branch_to_commit(self.rebase_state.destination_branch.commit)
        self.store_head()
        self.store_branch(self.head.branch)
        self.restore_repository_state(self.rebase_state.destination_branch.commit)
        self.rebase_state = None

    def rebase(self) -> RebaseState:
        while self.rebase_state.not_applied:
            not_applied_commit = self.rebase_state.not_applied.pop()
            self.apply_commit(not_applied_commit)
            if self.rebase_state.is_conflict:
                return self.rebase_state

        state = self.rebase_state
        self.rebase_state = None

        return state

    def apply_commit(self, commit: Commit):
        for item, item_hash in commit.tree.children.items():
            if item in self.rebase_state.resolved_files:
                continue
            self.rebase_state.current_file = item
            self.rebase_state.resolved_files.add(item)
            if item in self.rebase_state.destination_branch_changed:
                self.rebase_state.is_conflict = True
                # нужно составить файл с конфликтом
                branch_blob = Blob.deserialize(
                    CVSStorage.read_object(item_hash.hex(), Blob, self._full_path_to_objects))
                other_branch_file_lines = branch_blob.content.decode().splitlines(keepends=True)
                with open(item.path, 'r') as f:
                    curr_branch_file_lines = f.read().splitlines(keepends=True)
                create_diff_file(item.path, curr_branch_file_lines, other_branch_file_lines)
                # ждем разрешения конфликта
                return
        self.rebase_state.resolved_files = set()
        # текущий коммит можно применить
        commit.parent_commit_hash = self.rebase_state.current_dst_commit.get_hash()
        # сохранить на диск
        CVSStorage.store_object(
            commit.get_hash().hex(), commit.serialize(), Blob, self._full_path_to_objects)
        # сдвинуть head и текущую ветку
        self.head = self.move_head_with_branch_to_commit(commit)
        self.store_head()
        self.store_branch(self.head.branch)
        self.rebase_state.current_dst_commit = commit

    def restore_repository_state(self, commit: Commit):
        tree_files = self.expand_full_tree(commit)

        # удалить все что есть (кроме того, что в игноре)
        ignore = set(i.path for i in self.index.ignore)
        rmdir(self.path_to_repository, ignore)

        # восстановить копии из хранилища
        self._restore_tree(tree_files)

    def _restore_tree(self, files: dict[TreeObjectData, bytes]):
        for file, file_hash in files.items():
            file_data = CVSStorage.read_object(file_hash.hex(), file.object_type, self._full_path_to_objects)
            os.makedirs(os.path.dirname(file.path), exist_ok=True)
            blob = Blob.deserialize(file_data)
            with open(file.path, 'wb+') as f:
                f.write(blob.content)

    def get_commit_by_hash(self, commit_hash: str) -> Commit:
        raw_commit = CVSStorage.read_object(commit_hash, Commit, self._full_path_to_objects)

        return Commit.deserialize(raw_commit)

    def get_branch_by_name(self, branch_name: str) -> Branch:
        commit_hash = CVSStorage.read_object(branch_name,
                                            Branch,
                                            os.path.join(self.path_to_repository, FoldersEnum.HEADS))

        raw_commit = CVSStorage.read_object(commit_hash.decode(), Commit, self._full_path_to_objects)

        return Branch(branch_name, Commit.deserialize(raw_commit))

    def get_commit_by_tag_name(self, tag_name: str) -> Commit:
        commit_hash = CVSStorage.read_object(tag_name,
                                             Tag,
                                             os.path.join(self.path_to_repository, FoldersEnum.TAGS))

        raw_commit = CVSStorage.read_object(commit_hash.decode(), Commit, self._full_path_to_objects)

        return Commit.deserialize(raw_commit)

    def move_head_with_branch_to_commit(self, commit: Commit) -> Head:
        if self.head.is_point_to_branch:
            new_branch = Branch(self.head.branch.name, commit)
            return Head(new_branch)
        else:
            return Head(commit)

    def create_tag(self, tag_name: str, message=''):
        current_commit = self.get_commit_from_head()
        tag = Tag(tag_name, current_commit, message=message)
        CVSStorage.store_object(tag_name,
                                tag.get_pointer().hex().encode(),
                                Tag,
                                os.path.join(self.path_to_repository, FoldersEnum.TAGS))

    def delete_tag(self, tag_name: str):
        path_to_tag = os.path.join(self.path_to_repository, FoldersEnum.TAGS, tag_name)
        os.remove(path_to_tag)

    def delete_branch(self, branch_name: str):
        path_to_branch = os.path.join(self.path_to_repository, FoldersEnum.HEADS, branch_name)
        os.remove(path_to_branch)

    def store_head(self):
        if self.head.is_point_to_branch:
            CVSStorage.store_object('HEAD',
                                    self.head.get_pointer(),
                                    Head,
                                    os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))
        else:
            CVSStorage.store_object('HEAD',
                                    self.head.get_pointer().hex().encode(),
                                    Head,
                                    os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))

    def store_branch(self, branch: Branch):
        CVSStorage.store_object(branch.name,
                                branch.get_pointer().hex().encode(),
                                Branch,
                                os.path.join(self.path_to_repository, FoldersEnum.HEADS))

    @staticmethod
    def is_repository_exists(path_to_repository: str) -> bool:
        path_to_cvs_data = os.path.join(path_to_repository, FoldersEnum.CVS_DATA)

        return os.path.isdir(path_to_cvs_data)

    def _initialize_head(self):
        item = self._get_head_reference()
        self.head = Head(item)

    def get_commit_from_head(self) -> Commit:
        item = self._get_head_reference()
        if isinstance(item, Commit):
            return item
        else:
            return item.commit

    def get_branch_from_head(self) -> Branch:
        item = self._get_head_reference()
        if isinstance(item, Branch):
            return item

        raise ValueError('head does not point to a branch')

    def get_branches_names(self) -> list[str]:
        path_to_branches = os.path.join(self.path_to_repository, FoldersEnum.HEADS)

        return os.listdir(path_to_branches)

    def get_tags_names(self) -> list[str]:
        path_to_tags = os.path.join(self.path_to_repository, FoldersEnum.TAGS)

        return os.listdir(path_to_tags)

    def enumerate_commit_parents(self, commit: Commit, return_itself=False):
        current_commit = commit
        if return_itself:
            yield commit
        while current_commit.parent_commit_hash != b'':
            prev_commit = self.get_commit_by_hash(current_commit.parent_commit_hash.hex())
            if prev_commit.parent_commit_hash == b'':
                break
            yield prev_commit
            current_commit = prev_commit

    def enumerate_tree_files(self, tree: Tree) -> tuple[TreeObjectData, bytes]:
        for item, item_hash in tree.children.items():
            if item.object_type is Tree:
                nested_tree = CVSStorage.read_object(item_hash.hex(), Tree, self._full_path_to_objects)
                yield from self.enumerate_tree_files(Tree.deserialize(nested_tree))
            else:
                yield item, item_hash

    def _get_head_reference(self):
        head_reference = CVSStorage.read_object('HEAD',
                                                Reference,
                                                os.path.join(self.path_to_repository, FoldersEnum.CVS_DATA))
        if head_reference.decode().startswith('ref'):
            branch_name = os.path.basename(head_reference.decode())
            commit_hash = CVSStorage.read_object(
                branch_name, Branch, os.path.join(self.path_to_repository, FoldersEnum.HEADS))
            raw_commit = CVSStorage.read_object(commit_hash.decode(), Commit, self._full_path_to_objects)
            return Branch(branch_name, Commit.deserialize(raw_commit))
        else:
            raw_commit = CVSStorage.read_object(head_reference.decode(), Commit, self._full_path_to_objects)
            return Commit.deserialize(raw_commit)


class Index:
    def __init__(self, directory: str, cvs: CVS):
        self.directory = directory
        self.cvs = cvs
        self.ignore: set[TreeObjectData] = set()
        self.staged: set[TreeObjectData] = set()
        self.modified: dict[TreeObjectData, bytes] = {}
        self.removed: dict[TreeObjectData, bytes] = {}
        self.new: dict[TreeObjectData, bytes] = {}

    def compare_tree_to_dir(self, tree_files: dict[TreeObjectData, bytes]) -> "TreeComparisonResult":
        in_first: dict[TreeObjectData, bytes] = {}
        in_second: dict[TreeObjectData, bytes] = {}
        different: dict[TreeObjectData, bytes] = {}
        equal: dict[TreeObjectData, bytes] = {}
        res = TreeComparisonResult(in_first, in_second, different, equal)

        dir_tree_files = {item: item_hash for item, item_hash in self._enumerate_tree_files_from_directory(self.directory)}
        for first_tree_object_data in dir_tree_files:
            if first_tree_object_data not in tree_files:
                # current object is new
                in_first[first_tree_object_data] = dir_tree_files[first_tree_object_data]
            elif dir_tree_files[first_tree_object_data] != tree_files[first_tree_object_data]:
                # current object was changed
                different[first_tree_object_data] = dir_tree_files[first_tree_object_data]
            else:
                equal[first_tree_object_data] = dir_tree_files[first_tree_object_data]

        for item in tree_files:
            if item not in equal and item not in different:
                in_second[item] = tree_files[item]

        return res

    def update(self, commit: Commit):
        tree_files = self.cvs.expand_full_tree(commit)
        comp_res = self.compare_tree_to_dir(tree_files)
        self.new = comp_res.in_first
        self.removed = {TreeObjectData(data.path, data.object_type, is_removed=True): v
                        for data, v in comp_res.in_second.items()
                        if TreeObjectData(data.path, data.object_type, is_removed=True) not in tree_files}
        self.modified = comp_res.different

    def _enumerate_tree_files_from_directory(self, directory: str) -> tuple[TreeObjectData, bytes]:
        for file in os.listdir(directory):
            full_path = os.path.join(directory, file)
            if os.path.isdir(full_path):
                full_path = os.path.join(full_path, '')
                if TreeObjectData(full_path, Tree) in self.ignore:
                    continue
                yield from self._enumerate_tree_files_from_directory(full_path)
            else:
                if TreeObjectData(full_path, Blob) in self.ignore:
                    continue
                file_data = TreeObjectData(full_path, Blob)
                with open(full_path, 'rb') as f:
                    obj = Blob(f.read())

                yield file_data, obj.get_hash()


@dataclass
class TreeComparisonResult:
    in_first: dict["TreeObjectData", bytes]
    in_second: dict["TreeObjectData", bytes]
    different: dict["TreeObjectData", bytes]
    equal: dict["TreeObjectData", bytes]

    def extend(self, other: "TreeComparisonResult"):
        self.in_first.update(other.in_first)
        self.in_second.update(other.in_second)
        self.different.update(other.different)
        self.equal.update(other.equal)
