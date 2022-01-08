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
        self.index: Index = Index(path)
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
        self.index.update(self.get_full_tree_state(head_commit), self._full_path_to_objects)

    def rebase(self, branch: Branch) -> RebaseState:
        head_branch = self.get_branch_from_head()
        head_commit = head_branch.commit
        head_commit_parents = {parent for parent in self.enumerate_commit_parents(head_commit)}
        self.rebase_state = RebaseState(branch, head_branch)

        common_commit = None
        for branch_parent in self.enumerate_commit_parents(branch.commit):
            if branch_parent in head_commit_parents:
                common_commit = branch_parent
                break
            self.rebase_state.not_applied.append(branch_parent)

        for head_parent in self.enumerate_commit_parents(head_commit):
            self.rebase_state.dst_branch_changed.add(head_parent)
            if head_parent == common_commit:
                break

        self.rebase_state.current_dst_commit = head_commit

        return self._rebase()

    def continue_rebase(self) -> RebaseState:
        if not self.rebase_state or not self.rebase_state.is_conflict:
            raise ValueError('not in rebase')
        self.rebase_state.is_conflict = False

        return self._rebase()

    def abort_rebase(self):
        if not self.rebase_state:
            return
        # передвигаем head и branch в начальное положение
        self.move_head_with_branch_to_commit(self.rebase_state.destination_branch.commit)
        self.restore_repository_state(self.rebase_state.destination_branch.commit)
        self.rebase_state = None

    def _rebase(self) -> RebaseState:
        for not_applied_commit in self.rebase_state.not_applied:
            if not_applied_commit in self.rebase_state.applied:
                continue
            for item, item_hash in not_applied_commit.tree.children.items():
                if item in self.rebase_state.resolved_files:
                    continue
                self.rebase_state.current_file = item
                self.rebase_state.resolved_files.add(item)
                if item in self.rebase_state.dst_branch_changed:
                    self.rebase_state.is_conflict = True
                    # нужно составить файл с конфликтом
                    other_branch_file_lines = CVSStorage \
                        .read_object(item_hash.decode(), Blob, self._full_path_to_objects) \
                        .decode() \
                        .split()
                    with open(item.path, 'r') as f:
                        curr_branch_file_lines = f.readlines()
                    create_diff_file(item.path, curr_branch_file_lines, other_branch_file_lines)
                    # ждем разрешения конфликта
                    return self.rebase_state
            self.rebase_state.applied.add(not_applied_commit)
            self.rebase_state.resolved_files = set()
            # текущий коммит можно применить
            not_applied_commit.parent_commit_hash = self.rebase_state.current_dst_commit.get_hash()
            # сохранить на диск
            CVSStorage.store_object(
                not_applied_commit.get_hash().hex(), not_applied_commit.serialize(), Blob, self._full_path_to_objects)
            # сдвинуть head и текущую ветку
            self.move_head_with_branch_to_commit(not_applied_commit)
            self.rebase_state.current_dst_commit = not_applied_commit

        state = self.rebase_state
        self.rebase_state = None

        return state

    def restore_repository_state(self, commit: Commit):
        full_tree = self.get_full_tree_state(commit)

        # удалить все что есть (кроме того, что в игноре)
        ignore = set(i.path for i in self.index.ignore)
        rmdir(self.path_to_repository, ignore)

        # восстановить копии из хранилища
        self._restore_tree(full_tree)

    def _restore_tree(self, tree: Tree):
        for file, file_hash in tree.children.items():
            file_data = CVSStorage.read_object(file_hash.hex(), file.object_type, self._full_path_to_objects)
            if file.object_type is Tree:
                nested_tree = Tree.deserialize(file_data)
                self._restore_tree(nested_tree)
            else:
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

    def enumerate_commit_parents(self, commit: Commit):
        current_commit = commit
        while current_commit.parent_commit_hash != b'':
            prev_commit = self.get_commit_by_hash(current_commit.parent_commit_hash.hex())
            if prev_commit.parent_commit_hash == b'':
                break
            yield prev_commit
            current_commit = prev_commit

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
    def __init__(self, directory: str):
        self.directory = directory
        self.ignore: set[TreeObjectData] = set()
        self.staged: set[TreeObjectData] = set()
        self.modified: dict[TreeObjectData, bytes] = {}
        self.removed: dict[TreeObjectData, bytes] = {}
        self.new: dict[TreeObjectData, bytes] = {}

    @staticmethod
    def compare_trees(first: Tree, second: Tree, storage_path: str) -> "TreeComparisonResult":
        in_first: dict[TreeObjectData, bytes] = {}
        in_second: dict[TreeObjectData, bytes] = {}
        different: dict[TreeObjectData, bytes] = {}
        equal: dict[TreeObjectData, bytes] = {}
        res = TreeComparisonResult(in_first, in_second, different, equal)

        second_tree_objects_data = second.children.keys()
        for first_tree_object_data in first.children:
            if first_tree_object_data not in second_tree_objects_data:
                # current object is new
                in_first[first_tree_object_data] = first.children[first_tree_object_data]
            elif first.children[first_tree_object_data] != second.children[first_tree_object_data]:
                # current object was changed
                if first_tree_object_data.object_type == Tree:
                    first_subtree = Tree.initialize_from_directory(first_tree_object_data.path)
                    second_subtree = Tree.deserialize(CVSStorage.read_object(
                        second.children[first_tree_object_data].hex(),
                        Tree,
                        storage_path))
                    for item in second.children:
                        if item in second_subtree.children:
                            second_subtree.children[item] = second.children[item]
                    comp_res = Index.compare_trees(first_subtree, second_subtree, storage_path)
                    res.extend(comp_res)
                elif first_tree_object_data.object_type == Blob:
                    different[first_tree_object_data] = first.children[first_tree_object_data]
            else:
                equal[first_tree_object_data] = first.children[first_tree_object_data]

        for item in second.children:
            if item not in equal and item not in first.children:
                in_second[item] = second.children[item]

        return res

    def update(self, tree: Tree, storage_path: str):
        dir_tree = Tree.initialize_from_directory(self.directory)
        filtered_dir_tree = Tree()
        filtered_dir_tree.children = {k: v for k, v in dir_tree.children.items() if k not in self.ignore}

        comp_res = Index.compare_trees(filtered_dir_tree, tree, storage_path)
        self.new = comp_res.in_first
        self.removed = {TreeObjectData(data.path, data.object_type, is_removed=True): v
                        for data, v in comp_res.in_second.items()
                        if TreeObjectData(data.path, data.object_type, is_removed=True) not in tree.children}
        self.modified = comp_res.different


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
