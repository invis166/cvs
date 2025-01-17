import argparse
import cmd
import os

from modules.cvs import CVS
from modules.cvs_objects import Tree, TreeObjectData, Blob
from modules.references import Head, Branch
from modules.rebase_state import RebaseState


class ExitCmdExecution(Exception):
    pass


def print_commit_info(commit, verbose=True):
    print(f'{commit.get_hash().hex()} | {commit.message}')
    if not verbose:
        return
    print('changed files:')
    for data in commit.tree.children:
        if data.is_removed:
            print(f'removed: {data.path}')
        else:
            print(data.path)


class CVSShell(cmd.Cmd):
    intro = 'test'
    prompt = None

    def __init__(self):
        super(CVSShell, self).__init__()
        self.cvs: CVS = None
        self.path_to_repository = None
        self.working_directory = os.getcwd()
        self.do_cd(self.working_directory)

        self._create_and_delete_parser = None
        self._commit_parser = None
        self._rebase_parser = None
        self._reset_parser = None
        self._initialize_argparsers()

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
        arg = arg.split()
        try:
            values = vars(self._commit_parser.parse_args(arg))
        except SystemExit:
            return

        if values['m']:
            commit_message = ' '.join(values['m'])
        else:
            commit_message = ''
        if not values['i']:
            self.cvs.make_commit(commit_message)
        else:
            commit = self.cvs.get_commit_by_hash(values['i'])
            print_commit_info(commit)

    def do_status(self, arg: str):
        '''Show an index'''
        if not self.path_to_repository:
            print('not a repository')
            return

        self.cvs.update_index()
        if self.cvs.head.is_point_to_branch:
            print(f'current branch: {self.cvs.head.branch.name}')
        else:
            print(f'detached head: {self.cvs.head.commit.get_hash().hex()}')
        if self.cvs.rebase_state and self.cvs.rebase_state.is_conflict:
            print(f'rebasing {self.cvs.rebase_state.source_branch.name} on {self.cvs.rebase_state.destination_branch.name}')
        staged_filter = lambda x: x not in self.cvs.index.staged
        for new in filter(staged_filter, self.cvs.index.new):
            print(f'new: {new.path}')
        for removed in filter(staged_filter, self.cvs.index.removed):
            print(f'removed: {removed.path}')
        for modified in filter(staged_filter, self.cvs.index.modified):
            print(f'modified: {modified.path}')
        for staged in self.cvs.index.staged:
            print(f'staged: {staged.path}')

    def do_add(self, arg: str):
        '''Add specified file to a commit'''
        self.cvs.update_index()
        if arg == '.':
            to_add = os.listdir('.')
        else:
            to_add = arg.split(' ')
        for path in map(lambda path: os.path.join(self.path_to_repository, path), to_add):
            is_removed = not os.path.exists(path)
            if os.path.isdir(path) or is_removed and path.endswith(os.path.sep):
                data = TreeObjectData(os.path.join(path, ''), Tree, is_removed=is_removed)
            else:
                data = TreeObjectData(path, Blob, is_removed=is_removed)
            self.cvs.add_to_staged(data)

    def do_reset(self, arg):
        '''Move head and current branch to specified commit
        reset [--hard] commit'''
        arg = arg.split()
        if len(arg) == 1:
            commit_hash = arg[0]
        else:
            commit_hash = arg[1]

        try:
            commit = self.cvs.get_commit_by_hash(commit_hash)
        except FileNotFoundError:
            print(f'can not find commit with hash {commit_hash}')
            return

        head = self.cvs.move_head_with_branch_to_commit(commit)
        self.cvs.head = head
        self.cvs.store_head()
        if self.cvs.head.is_point_to_branch:
            self.cvs.store_branch(self.cvs.head.branch)
        if len(arg) == 2 and arg[0] == '--hard':
            self.cvs.restore_repository_state(commit)

    def do_switch(self, arg: str):
        '''Move head to a branch'''
        try:
            branch = self.cvs.get_branch_by_name(arg)
        except FileNotFoundError:
            print('can not find specified branch')
            return

        self.cvs.head = Head(branch)
        self.cvs.store_head()

    def do_checkout(self, arg: str):
        '''Move head to a commit'''
        if not arg:
            print('pass the argument')
            return
        try:
            from_hash = self.cvs.get_commit_by_hash(arg)
        except FileNotFoundError:
            from_hash = None
        try:
            from_tag = self.cvs.get_commit_by_tag_name(arg)
        except FileNotFoundError:
            from_tag = None
        if not from_tag and not from_hash:
            print('can not find specified commit')
            return

        commit = from_tag or from_hash
        self.cvs.head = Head(commit)
        self.cvs.store_head()

    def do_tag(self, arg: str):
        '''Create/Delete tag'''
        arg = arg.split(' ')
        try:
            values = vars(self._create_and_delete_parser.parse_args(arg))
        except SystemExit:
            return

        tag_name = values['c'] or values['d']
        if values['l']:
            for name in self.cvs.get_tags_names():
                print(name)
        elif values['c']:
            self.cvs.create_tag(tag_name)
        else:
            self.cvs.delete_tag(tag_name)

    def do_branch(self, arg):
        '''Create/Delete/List branch'''
        arg = arg.split(' ')
        try:
            values = vars(self._create_and_delete_parser.parse_args(arg))
        except SystemExit:
            return

        branch_name = values['c'] or values['d']
        if values['l']:
            for branch_name in self.cvs.get_branches_names():
                print(branch_name)
        elif values['c']:
            branch = Branch(branch_name, self.cvs.get_commit_from_head())
            self.cvs.store_branch(branch)
        else:
            self.cvs.delete_branch(branch_name)

    def do_rebase(self, arg):
        '''Rebase branches
        rebase [-i|--interactive] branch_name
        rebase [-o|--onto] first_branch second_branch
        rebase [-a|--abort]
        '''
        arg = arg.split()
        if len(arg) == 1 and not arg[0][0] == '-':
            branch = self.cvs.get_branch_by_name(arg[0])
            self.cvs.initialize_rebase_state(branch)
            res = self.cvs.rebase()
            self._handle_rebase_state(res)
        else:
            values = vars(self._rebase_parser.parse_args(arg))
            if values['continue']:
                res = self.cvs.continue_rebase()
                self._handle_rebase_state(res)
            elif values['onto']:
                first, second = map(self.cvs.get_branch_by_name, values['onto'])
                self.cvs.initialize_rebase_state(second)
                self.cvs.rebase_state.not_applied = []
                for c in self.cvs.enumerate_commit_parents(second.commit, return_itself=True):
                    if c == first.commit:
                        break
                    self.cvs.rebase_state.not_applied.append(c)
                self._handle_rebase_state(self.cvs.rebase())
            elif values['interactive']:
                self._handle_interactive_rebase(values['interactive'])
            elif values['abort']:
                self.cvs.abort_rebase()

    def do_log(self, arg):
        '''Show all commits up to the first'''
        commit = self.cvs.get_commit_from_head()
        print_commit_info(commit)
        print('-' * 20)
        for parent in self.cvs.enumerate_commit_parents(commit):
            print_commit_info(parent)
            print('-' * 20)

    def do_ls(self, arg: str):
        '''Show all files in specified directory'''
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

    def _handle_interactive_rebase(self, branch_name: str):
        try:
            InteractiveRebaseShell(self.cvs, branch_name).cmdloop()
        except ExitCmdExecution:
            self.cvs.rebase_state = None
            self.cvs.restore_repository_state(self.cvs.head.branch.commit)

    def _initialize_argparsers(self):
        self._create_and_delete_parser = argparse.ArgumentParser()
        group = self._create_and_delete_parser.add_mutually_exclusive_group()
        group.add_argument('-c', type=str, help='create')
        group.add_argument('-d', type=str, help='delete')
        group.add_argument('-l', action='store_true', help='list')

        self._commit_parser = argparse.ArgumentParser()
        self._commit_parser.add_argument('-m', nargs='*', help='commit message')
        self._commit_parser.add_argument('-i', help='get commit info')

        self._rebase_parser = argparse.ArgumentParser()
        self._rebase_parser.add_argument('-i', '--interactive', help='interactive mode')
        self._rebase_parser.add_argument('-o', '--onto', nargs=2)
        self._rebase_parser.add_argument('-a', '--abort', action='store_true', help='abort rebase')
        self._rebase_parser.add_argument('-c', '--continue', action='store_true', help='continue rebse')

    def _handle_rebase_state(self, res: RebaseState):
        if res.is_conflict:
            print(f'can not finish rebase, please resolve conflict in {res.current_file.path}'
                  f' and continue rebase, or abort it. To apply changes, add files to staged')
        else:
            print(f'successfully rebase {res.source_branch.name} on {res.destination_branch.name}')
            self.cvs.restore_repository_state(self.cvs.head.branch.commit)
            for commit in res.applied:
                print_commit_info(commit, verbose=False)

    def _set_working_directory(self, directory: str):
        self.working_directory = os.path.abspath(directory)
        os.chdir(self.working_directory)
        CVSShell.prompt = f'{self.working_directory}$ '


class InteractiveRebaseShell(cmd.Cmd):
    prompt = '(interactive rebase) > '

    def __init__(self, cvs: CVS, branch_name: str):
        super().__init__()
        self.cvs = cvs
        self.cvs.initialize_rebase_state(self.cvs.get_branch_by_name(branch_name))
        self.not_applied_commits = self.cvs.rebase_state.not_applied
        self._show_info()

    def do_pick(self, arg):
        '''pick <commit> = use commit'''
        commit = self.cvs.get_commit_by_hash(arg)
        self.cvs.apply_commit(commit)
        if self.cvs.rebase_state.is_conflict:
            print(f'resolve conflict in {self.cvs.rebase_state.current_file.path} and type "apply"')
        for c in self.not_applied_commits:
            if c.get_hash().hex() == arg:
                self.not_applied_commits.remove(c)
        self._show_info()

    def do_reword(self, arg):
        '''reword <commit> <msg> = use commit, but edit the commit message'''
        arg = arg.split()
        commit_hash = arg[0]
        msg = ' '.join(arg[1:])
        commit = self.cvs.get_commit_by_hash(commit_hash)
        commit.message = msg
        self.cvs.apply_commit(commit)
        if self.cvs.rebase_state.is_conflict:
            print(f'resolve conflict in {self.cvs.rebase_state.current_file}')
        for c in self.not_applied_commits:
            if c.get_hash().hex() == commit_hash:
                self.not_applied_commits.remove(c)
        self._show_info()

    def do_edit(self, arg):
        '''edit <commit> = use commit, but stop for amending. type "apply" after finishing'''
        commit = self.cvs.get_commit_by_hash(arg)
        self.cvs.restore_repository_state(commit)
        self.not_applied_commits.remove(commit)
        self._show_info()

    def do_drop(self, arg):
        '''drop <commit> = remove commit'''
        commit = self.cvs.get_commit_by_hash(arg)
        self.not_applied_commits.remove(commit)
        self._show_info()

    def do_break(self, arg):
        '''break = stop merge'''
        raise ExitCmdExecution()

    def do_abort(self, arg):
        self.cvs.abort_rebase()
        raise ExitCmdExecution()

    def do_apply(self, arg):
        '''apply <message> = do after finishing editing or to resolve conflict'''
        self.cvs.update_index()
        self.cvs.index.staged = self.cvs.index.modified.copy()
        self.cvs.make_commit(arg)
        self._show_info()

    def _show_info(self):
        if not self.not_applied_commits:
            raise ExitCmdExecution()
        for commit in self.not_applied_commits:
            print(f'{commit.get_hash().hex()} | {commit.message}')
        print('type "help" to see available commands')


if __name__ == '__main__':
    CVSShell().cmdloop()
