import argparse
from contextlib import contextmanager
import errno
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from textwrap import TextWrapper
from typing import OrderedDict
from urllib.parse import urlparse
from urllib.request import urlopen

# Utilites


@contextmanager
def cwd(path):
    d0 = os.getcwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(d0)


def mkdir_p(dir):
    if dir == '':
        return
    try:
        return os.makedirs(dir, exist_ok=True)
    except TypeError:
        pass
    try:
        return os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST or os.path.isfile(dir):
            raise


def relpath(dir, rel):
    return os.path.abspath(os.path.join(dir, rel))


def rm_rf(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def tempfilepath(prefix=None, suffix=None):
    if sys.version_info < (3, 0):
        if prefix is None:
            prefix = ''
        if suffix is None:
            suffix = ''
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    os.close(fd)
    return path


def wget(url, dest="", tempdir=False):
    if dest == "":
        dest = os.path.basename(url)
        if dest == "":
            dest = tempfilepath()
        elif tempdir:
            dest = os.path.join('/tmp', dest)
    ufile = urlopen(url)
    data = ufile.read()
    with open(dest, "wb") as file:
        file.write(data)
    return os.path.abspath(dest)


class Runner:
    def __init__(self, nop=False):
        self.nop = nop

    # sudo: True/False/"file"
    def run(self, cmd, at=None, output=None, nop=None, _try=False):
        cmd_file = None
        if cmd.find('\n') > -1:
            cmds1 = str.lstrip(TextWrapper.dedent(cmd))
            cmds = filter(lambda s: str.lstrip(s) != '', cmds1.split("\n"))
            cmd = "; ".join(cmds)
            cmd_for_log = cmd
        else:
            cmd_for_log = cmd
        print(cmd)
        if cmd_file is not None:
            print("# {}".format(cmd_for_log))
        sys.stdout.flush()
        if nop is None:
            nop = self.nop
        if nop:
            return
        if output != True:
            fd, temppath = tempfile.mkstemp()
            os.close(fd)
            cmd = "{{ {CMD}; }} >{LOG} 2>&1".format(CMD=cmd, LOG=temppath)
        if at is None:
            rc = subprocess.call(["bash", "-e", "-c", cmd])
        else:
            with cwd(at):
                rc = os.system(cmd)
        if rc > 0:
            logging.error("command failed: " + cmd_for_log)
            sys.stderr.flush()
        if output != True:
            os.remove(temppath)
        if cmd_file is not None:
            os.remove(cmd_file)
        if rc > 0 and not _try:
            sys.exit(1)
        return rc

    def has_command(self, cmd):
        return Runner.has_command(cmd)

    @staticmethod
    def has_command(cmd):
        return os.system("command -v " + cmd + " > /dev/null") == 0


def die(msg: str) -> None:
    logging.error(msg)
    exit(1)


def log_func(args: list) -> None:
    caller = sys._getframe(1).f_code.co_name
    logging.debug('called %s(%s)', caller, args)


def log_dict(msg, obj, *props):
    d = {prop: obj.get(prop, None) for prop in props}
    logging.info(f'{msg} {d}')


def load_dict(path: str, log=True) -> dict:
    _, name = os.path.split(path)
    _, ext = os.path.splitext(path)
    with open(path, 'r') as f:
        if ext == '.json':
            o = json.load(f)
        elif ext in ['.yml', '.yaml']:
            import yaml
            o = yaml.load(f, Loader=yaml.FullLoader)
        else:
            logging.error(f'Unknown extension {ext} for {path} - aborting.')
            exit(1)
    if log:
        log_dict(f'Loaded {name}', o, 'id', 'type', 'name')
    return o


def dump_dict(path: str, map: dict, log=True) -> None:
    _, name = os.path.split(path)
    _, ext = os.path.splitext(path)
    with open(path, 'w') as f:
        if ext == '.json':
            json.dump(map, f, indent=4)
        elif ext in ['.yml', '.yaml']:
            import yaml
            yaml.dump(map, f)
        else:
            logging.error(f'Unknown extension {ext} for {path} - aborting.')
            exit(1)
    if log:
        log_dict(f'Dumped {name}', map, 'id', 'type', 'name')


def command_filename(name):
    """ Return the filename for a command """
    return name.lower().replace(' ', '-')


def do_or_die(args: list, cwd='./') -> bytes:
    log_func(locals())
    sp = subprocess.Popen(
        args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = sp.communicate()
    if sp.returncode != 0:
        logging.error(err.decode('utf-8'))
        exit(sp.returncode)
    return out.decode('utf-8')


def git_get(uri: str, dest: str, skip_clone: bool = True) -> str:
    log_func(locals())
    _uri = urlparse(uri)
    _, name = os.path.split(_uri.path)
    name, ext = os.path.splitext(name)
    if _uri.scheme == 'https' and ext in ['', '.git']:
        if not skip_clone:
            do_or_die(['rm', '-rf', dest])
            do_or_die(['mkdir', '-p', dest])
            do_or_die(['git', 'clone', uri, dest])
            do_or_die(['git', 'fetch', '--all', '--tags'], dest)
        return dest
    elif (_uri.scheme == 'file' or _uri.scheme == '') and ext == '':
        return _uri.path
    else:
        logging.error('Cannot determine git repo - aborting.')
        exit(1)




def filter_by_res(elems: list, include: str, exclude: list) -> list:
    log_func(locals())
    e = [re.match(include, elem) for elem in elems]
    e = [elem[1] for elem in e if elem]
    for ex in exclude:
        e = [x for x in e if not re.match(ex, x)]
    e.sort(reverse=True)
    return e


def get_tags(repo_path: str, res: dict) -> list:
    tags = do_or_die(['git', 'tag'], cwd=repo_path).split('\n')
    tags = filter_by_res(tags, res.get('include_tag_regex'),
                         res.get('exclude_tag_regexes'))
    return tags


def get_branches(repo_path: str, res: dict) -> list:
    branches = do_or_die(['git', 'branch', '-r'], cwd=repo_path).split('\n')
    branches = [branch.strip() for branch in branches]
    branches = filter_by_res(branches, f'origin/({res.get("include_branch_regex")})',
                             [f'origin/({bre})' for bre in res.get('exclude_branch_regexes')])
    return branches


def get_dev_docs(website: dict, piece: dict, piece_path: str, commands: dict) -> dict:
    ''' Gets dev commands and docs '''
    typo = piece.get('type')
    docs = piece.get('docs', None)
    docs_repo = f'{piece_path}/docs_repo'
    if typo == 'docs':
        docs_repo = piece_path
    docs_git_uri = docs.get('git_uri')
    docs_repo = git_get(docs_git_uri, docs_repo, args.skip_clone)
    docs_dev_branch = None
    docs_branches_postfix = docs.get('branches_postfix', '')
    docs_repo_path = docs.get('path', '/')
    docs_commands = f'{docs_repo}/{docs.get("commands")}'
    docs_dev_branch = docs.get('dev_branch')
    website_path = website.get('path')
    website_content = f'{website_path}/{website.get("content")}'
    website_commands = f'{website_content}/commands/'
    website_docs = f'{website_content}'

    if typo == 'module':
        website_docs = f'{website_docs}/docs/{website.get("stack_docs")}/{piece.get("stack_path")}'
    for d in [
        website_content,
        website_commands,
        website_docs
    ]:
        do_or_die(['mkdir', '-p', d])

    do_or_die(
        ['git', 'checkout', f'origin/{docs_dev_branch}{docs_branches_postfix}'], cwd=docs_repo)

    payload = []
    if typo in ['core', 'module']:
        payload.append((f'{docs_repo}/{docs_repo_path}/docs', website_docs))
        cmds = get_commands(docs_commands, commands)
        for cmd in cmds.keys():
            payload.append(
                (f'{docs_repo}/{docs_repo_path}/commands/{command_filename(cmd)}.md', website_commands))
        commands.update(cmds)
    if typo == 'core':
        payload.append(
            (f'{docs_repo}/{docs_repo_path}/commands/_index.md', website_commands))
    elif typo == 'docs':
        payload.append((f'{docs_repo}/{docs_repo_path}/', website_content))
    payload += [(f'{docs_repo}/{p}', website_docs)
                for p in docs.get('copy', [])]

    rels = piece.get('releases', None)
    rels_repo = f'{piece_path}/rels_repo'
    if type(rels) is dict:
        source = rels.get('source', None)
        if source not in piece:
            logging.error(
                f'Invalid releases source key for {id} - aborting.')
        if source == 'docs':
            rels_repo = docs_repo
        elif source == 'repository':
            git_get(piece.get(source).get(
                'git_uri'), rels_repo, args.skip_clone)

    if rels:
        tags = []
        if rels.get('tags', False):
            tags = get_tags(rels_repo, rels)
        branches = get_branches(rels_repo, rels)

    for (s, d) in payload:
        do_or_die(['rsync', '-av', '--no-owner', '--no-group', s, d])

    return commands


# ------------------------------------------------------------------------------


class Component(dict):
    def __init__(self, path=None):
        super().__init__()
        if path:
            self.update(load_dict(path))
        self._exec = []
        self._id = self.get('id')
        self._type = self.get('type')
        self._name = self.get('name', '')
        self._description = self.get('description', '')

    def _get_commands(self):
        docs = self.get('docs')
        git_uri = docs.get('git_uri')
        
        
        cmds = load_dict()
        sinter = set(cmds).intersection(set(commands))
        if len(sinter) != 0:
            logging.error(f'Duplicate commands found - aborting.')
            logging.error(sinter)
            exit(1)

        return cmds


    def _apply_core(self):
        self._get_commands()

    def apply(self):
        logging.info(f'Applying {self._type} {self._id}')
        if self._type == 'core':
            self._apply_core()
        elif self._type == 'docs':
            self._apply_docs()
        elif self._type == 'module':
            self._apply_module()
        else:
            logging.error(f'Unknown component type: {self._type} - aborting.')
            exit(1)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--stack', type=str,
                        default='./data/stack.json',
                        help='path to stack definition')
    parser.add_argument('--skip-clone', action='store_true',
                        help='skips `git clone`')
    parser.add_argument('--loglevel', type=str,
                        default='INFO',
                        help='Python logging level (overwrites LOGLEVEL env var)')
    parser.add_argument('--tempdir', type=str,
                        help='temporary path', default=f'{tempfile.gettempdir()}')
    return parser.parse_args()

if __name__ == '__main__':
    # Init
    ARGS = parse_args()
    LOGLEVEL = os.environ.get('LOGLEVEL', ARGS.loglevel)
    logging.basicConfig(
        level=LOGLEVEL, format='%(levelname)s %(asctime)s %(message)s')
    mkdir_p(ARGS.tempdir)

    # Load settings
    DIRNAME = os.path.dirname(ARGS.stack)
    _, EXT = os.path.splitext(ARGS.stack)
    STACK = load_dict(ARGS.stack)

    # Compose the stack
    groups = OrderedDict()
    commands = OrderedDict()
    for component_file in STACK.get('components'):
        c = Component(path=f'{DIRNAME}/{component_file}{EXT}')
        c.apply()
        break

    # ---
    # website_content = f'{website_path}/{website.get("content")}'

    # groups = OrderedDict(load_dict(f'{args.data}/groups.json'))
    # commands = OrderedDict()
    # for piece_file in stack['pieces']:
    #     piece = load_dict(f'{args.data}/components/{piece_file}')
    #     id = piece.get('id')
    #     typo = piece.get('type')
    #     logging.info(f'Processing {typo} {id}...')

    #     name = piece.get('name', id)
    #     piece_path = f'{temp_dir}/{id}'

    #     if typo == 'core':
    #         commands = get_dev_docs(website, piece, piece_path, commands)
    #     elif typo == 'module':
    #         commands = get_dev_docs(website, piece, piece_path, commands)
    #         groups.update({
    #             piece.get('id'): {
    #                 'type': 'module',
    #                 'display': piece.get('name'),
    #                 'description': piece.get('description'),
    #             }
    #         })
    #     elif typo == 'docs':
    #         get_dev_docs(website, piece, piece_path, {})

    # dump_dict(f'{website_content}/commands.json', commands)
    # dump_dict(f'{args.data}/groups.json', groups)
