from commit import Commit


class CommitTree:
    def __init__(self):
        self.current_branch = Branch('main')
        head: Vertex

    def commit_to_head(self, commit: Commit):
        pass

    def change_head(self, commit: Commit):
        pass

    def create_branch(self, branch_name: str):
        self.current_branch.add_branch(branch_name)


class Branch:
    def __init__(self, name: str):
        self.name = name
        self.last_vertex = Vertex(None, None)

    def commit(self):
        pass

    def add_branch(self, branch: "Branch"):
        pass


class Vertex:
    def __init__(self, commit: Commit, previous: 'Vertex'):
        self.commit = commit
        self.previous = previous
