from datetime import datetime
from diff import Diff


class Commit:
    def __init__(self, date: datetime, diff: Diff):
        self.date = date
        self.diff = diff
        self.hash: int
