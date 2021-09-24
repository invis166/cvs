import cmd


class CVSShell(cmd.Cmd):
    intro = 'test'
    prompt = '> '

    #----- basic cvs commands -----
    def do_init(self, arg):
        print(f'{arg=}')


if __name__ == '__main__':
    CVSShell().cmdloop()
