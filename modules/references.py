class Reference:
    pass


class Branch(Reference):
    '''Branch is a reference to a commit'''
    def __init__(self, name: str, commit: "Commit"):
        self.name = name
        self.commit = commit

    def get_hash(self) -> bytes:
        pass


class Head(Reference):
    '''Head is a reference to a current branch'''
    def __init__(self, branch: "Branch"):
        self.branch = branch

    def get_hash(self) -> bytes:
        pass
