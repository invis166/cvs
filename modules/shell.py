import cmd
import os

from folders_enum import FoldersEnum
from cvs import CVS
from helpers import Helpers
from modules.cvs_objects import Tree, TreeObjectData, Blob


class CVSShell(cmd.Cmd):
    intro = 'test'
    prompt = None

    def __init__(self):
        super(CVSShell, self).__init__()
        self.cvs = None
        self.path_to_repository = None
        self.working_directory = os.getcwd()
        self.do_cd(self.working_directory)

    def do_init(self, arg: str):
        '''Initialize repository'''
        if CVS.is_repository_exists(self.working_directory):
            return

        self.cvs = CVS(self.working_directory)
        self.cvs.initialize_repository()
        self.path_to_repository = self.working_directory

        print(f'initialized repository at {self.working_directory}')

    def do_commit(self, arg: str):
        '''Create a new commit'''
        self.cvs.make_commit()

    def do_status(self, arg: str):
        '''Show an index'''
        if not self.path_to_repository:
            print('not a repository')
            return

        self.cvs.update_index()
        staged_filter = lambda x: x not in self.cvs.index.staged
        for new in filter(staged_filter, self.cvs.index.new):
            print(f'new: {new}')
        for removed in filter(staged_filter, self.cvs.index.removed):
            print(f'removed: {removed}')
        for modified in filter(staged_filter, self.cvs.index.modified):
            print(f'modified: {modified}')
        for staged in self.cvs.index.staged:
            print(f'staged: {staged}')

    def do_add(self, arg: str):
        self.cvs.update_index()
        if arg == '.':
            to_add = os.listdir('.')
        else:
            to_add = arg.split(' ')
        for path in map(os.path.abspath, to_add):
            if os.path.isdir(path):
                data = TreeObjectData(os.path.join(path, ''), Tree)
            else:
                data = TreeObjectData(path, Blob)
            self.cvs.add_to_staged(data)

    def do_ls(self, arg: str):
        for item in os.listdir(self.working_directory):
            print(item)

    def do_cd(self, arg: str):
        '''Change working directory'''
        directory = os.path.abspath(arg)
        if not os.path.exists(directory):
            print(f'can not find directory: {directory}')
            return

        self._set_working_directory(directory)
        if CVS.is_repository_exists(directory):
            # перешли в папку с репозиторием
            self.cvs = CVS(directory)
            self.cvs.initialize_repository()
            self.path_to_repository = directory
        elif self.path_to_repository \
                and os.path.commonprefix([directory, self.path_to_repository]) != self.path_to_repository:
            # покинули папку с репозиторием
            self.cvs = None
            self.path_to_repository = None

    def do_mkdir(self, arg: str):
        '''Create new directory'''
        try:
            os.mkdir(os.path.abspath(arg))
        except FileExistsError:
            print(f'directory {os.path.realpath(arg)} already exists')

    def _set_working_directory(self, directory: str):
        self.working_directory = os.path.abspath(directory)
        os.chdir(self.working_directory)
        CVSShell.prompt = f'{self.working_directory}$ '


if __name__ == '__main__':
    CVSShell().cmdloop()
