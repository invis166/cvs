import cmd
import os
from folders_enum import FoldersEnum


class CVSShell(cmd.Cmd):
    intro = 'test'
    prompt = None

    def __init__(self):
        super(CVSShell, self).__init__()
        self.repository_directory = None
        self._set_working_directory(os.getcwd())
        self.cvs = None

    def do_init(self, arg: str):
        '''Initialize repository'''
        print('not implemented')

    def do_commit(self, arg: str):
        '''Create a new commit'''
        print('not implemented')

    def do_status(self, arg: str):
        '''Show an index'''
        print('not implemented')

    def do_ls(self, arg: str):
        for item in os.listdir(self.current_directory):
            print(item)

    def do_cd(self, arg: str):
        '''Change working directory'''
        directory = os.path.abspath(arg)
        if not os.path.exists(directory):
            print(f'can not find directory: {directory}')
        else:
            if self._is_directory_a_repository(directory):
                self.repository_directory = directory
            self._set_working_directory(directory)

    def do_mkdir(self, arg: str):
        '''Create new directory'''
        try:
            os.mkdir(os.path.abspath(arg))
        except FileExistsError:
            print(f'directory {os.path.realpath(arg)} already exists')

    def _set_working_directory(self, directory: str):
        self.current_directory = os.path.abspath(directory)
        os.chdir(self.current_directory)
        CVSShell.prompt = f'{self.current_directory}$ '

    @staticmethod
    def _is_directory_a_repository(directory) -> bool:
        return os.path.exists(os.path.join(os.path.abspath(directory), FoldersEnum.CVS_DATA))


if __name__ == '__main__':
    CVSShell().cmdloop()
