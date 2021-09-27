import cmd
import os
from cvs import CVS


class CVSShell(cmd.Cmd):
    intro = 'test'
    prompt = None

    def __init__(self):
        super(CVSShell, self).__init__()
        self.repository_directory = None
        self.cvs_data_directory_name = '.cool_cvs'
        self._set_working_directory(os.getcwd())
        self.cvs = CVS()

    # ----- basic cvs commands -----
    def do_init(self, arg: str):
        '''Initialize repository'''
        self.repository_directory = self.current_directory
        try:
            os.mkdir(os.path.join(self.current_directory, self.cvs_data_directory_name))
        except FileExistsError:
            print('repository already exists')

    def do_commit(self, arg: str):
        '''Create a new commit'''
        print('not implemented')

    def do_status(self, arg: str):
        '''Show an index'''
        print('not implemented')

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

    # ---- utilities -----
    def _set_working_directory(self, directory: str):
        self.current_directory = os.path.abspath(directory)
        os.chdir(self.current_directory)
        CVSShell.prompt = f'{self.current_directory}$ '

    def _is_directory_a_repository(self, directory) -> bool:
        return os.path.exists(os.path.join(os.path.abspath(directory), self.cvs_data_directory_name))


if __name__ == '__main__':
    CVSShell().cmdloop()
