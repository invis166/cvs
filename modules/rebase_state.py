from modules.references import Branch
from modules.cvs_objects import Commit, TreeObjectData


class RebaseState:
    def __init__(self, source_branch: Branch, destination_branch: Branch):
        self.source_branch = source_branch
        self.destination_branch = destination_branch
        self.current_dst_commit = self.source_branch.commit
        self.current_file: TreeObjectData = None
        self.applied: set[Commit] = set()
        self.not_applied: list[Commit] = []
        self.destination_branch_changed: set[TreeObjectData] = set()
        self.resolved_files: set[TreeObjectData] = set()
        self.is_conflict = False
