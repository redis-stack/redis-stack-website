import argparse
from calendar import c
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
from typing import AnyStr, OrderedDict, Tuple
from urllib.parse import urlparse, ParseResult
from urllib.request import urlopen

# ------------------------------------------------------------------------------
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


def run(cmd, cwd=None, nop=None, _try=False):
    if cmd.find('\n') > -1:
        cmds1 = str.lstrip(TextWrapper.dedent(cmd))
        cmds = filter(lambda s: str.lstrip(s) != '', cmds1.split("\n"))
        cmd = "; ".join(cmds)
        cmd_for_log = cmd
    else:
        cmd_for_log = cmd
    logging.debug(f'run: {cmd}')
    sys.stdout.flush()
    if nop:
        return
    sp = subprocess.Popen(["bash", "-e", "-c", cmd],
                          cwd=cwd,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    out, err = sp.communicate()
    if sp.returncode != 0:
        logging.error(f'command failed: {cmd_for_log}')
        logging.error(err.decode('utf-8'))
        if not _try:
            die()
    return out.decode('utf-8')


def die(msg: str = 'aborting - have a nice day!') -> None:
    logging.error(msg)
    exit(1)


def rsync(src: str, dst: str, exclude: list = ['.*']):
    ex = [f'"{x}"' for x in exclude]
    return run(f'rsync -av --no-owner --no-group --exclude={{{",".join(ex)}}} {src} {dst}')


def log_func(args: list) -> None:
    caller = sys._getframe(1).f_code.co_name
    logging.debug('called %s(%s)', caller, args)


def log_dict(msg, obj, *props):
    d = {prop: obj.get(prop, None) for prop in props}
    logging.info(f'{msg} {d}')


def load_dict(filepath: str) -> dict:
    _, name = os.path.split(filepath)
    _, ext = os.path.splitext(filepath)
    with open(filepath, 'r') as f:
        if ext == '.json':
            o = json.load(f)
        elif ext in ['.yml', '.yaml']:
            import yaml
            o = yaml.load(f, Loader=yaml.FullLoader)
        else:
            die(f'Unknown extension {ext} for {filepath} - aborting.')
    return o


def dump_dict(filepath: str, map: dict) -> None:
    _, ext = os.path.splitext(filepath)
    with open(filepath, 'w') as f:
        if ext == '.json':
            json.dump(map, f, indent=4)
        elif ext in ['.yml', '.yaml']:
            import yaml
            yaml.dump(map, f)
        else:
            logging.error(
                f'Unknown extension {ext} for {filepath} - aborting.')
            exit(1)


def parseUri(uri: str) -> Tuple[ParseResult, str, str]:
    _uri = urlparse(uri)
    dirname = os.path.dirname(ARGS.stack)
    _, name = os.path.split(_uri.path)
    _, ext = os.path.splitext(name)
    return _uri, dirname, name, ext


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
def command_filename(name: str) -> str:
    return name.lower().replace(' ', '-')


class Markdown:
    def __init__(self, filepath: str):
        self.filepath = filepath
        with open(self.filepath, 'r') as f:
            self.payload = f.read()

    def persist(self):
        with open(self.filepath, 'w') as f:
            f.write(self.payload)

    @staticmethod
    def get_command_tokens(arguments: dict) -> set:
        """ Extract tokens from command arguments """
        rep = set()
        if type(arguments) is list:
            for arg in arguments:
                rep = rep.union(Markdown.get_command_tokens(arg))
        else:
            if 'token' in arguments:
                rep.add(arguments['token'])
            if 'arguments' in arguments:
                for arg in arguments['arguments']:
                    rep = rep.union(Markdown.get_command_tokens(arg))
        return rep

    @staticmethod
    def make_command_linkifier(commands: dict, name: str, data: dict):
        """
        Returns a function (for re.sub) that converts valid ticked command names to
        markdown links. This excludes the command in the context, as well as any of
        its arguments' tokens.
        """
        exclude = set(name)
        exclude.union(Markdown.get_command_tokens(data))

        def linkifier(m):
            command = m.group(1)
            if command in commands and command not in exclude:
                return f'[`{command}`](/commands/{command_filename(command)})'
            elif command.startswith('!'):
                return f'`{command[1:]}`'
            else:
                return m.group(0)
        return linkifier

    def generate_commands_links(self, name: str, commands: dict, payload: str) -> str:
        """ Generate markdown links for back-ticked commands """
        data = commands.get(name)
        linkifier = Markdown.make_command_linkifier(commands, name, data)
        rep = re.sub(r'`([A-Z][A-Z-_ \.]*)`', linkifier, payload)
        return rep

    @staticmethod
    def get_cli_shortcode(m):
        snippet = m[1]
        start = f'{{{{% redis-cli %}}}}\n'
        end = f'\n{{{{% /redis-cli %}}}}\n'
        return f'{start}{snippet}{end}'

    @staticmethod
    def convert_cli_snippets(payload):
        """ Convert the ```cli notation to Hugo shortcode syntax """
        rep = re.sub(r'```cli\n(.*)\n```\n', Markdown.get_cli_shortcode, payload, flags=re.S)
        return rep

    def add_command_frontmatter(self, name, commands):
        data = commands.get(name)
        data.update({
            'title': name,
            'description': data.get('summary')
        })
        if 'replaced_by' in data:
            data['replaced_by'] = self.generate_commands_links(
                name, commands, data.get('replaced_by'))
        self.payload = f'{json.dumps(data, indent=4)}\n\n{self.payload}'

    def process_command(self, name, commands):
        self.payload = self.generate_commands_links(name, commands, self.payload)
        self.convert_cli_snippets(name)
        self.add_command_frontmatter(name, commands)
        self.persist()


class Component(dict):
    def __init__(self, filepath: str = None, skip_clone: bool = False, tempdir: AnyStr = ''):
        super().__init__()
        if filepath:
            self._uri, self._dirname, self._filename, self._ext = parseUri(
                filepath)
            self.update(load_dict(filepath))
        self._skip_clone = skip_clone
        self._tempdir = f'{tempdir}/{self.get("id")}'

    def _git_clone(self, repo) -> str:
        git_uri = repo.get('git_uri')
        uri, _, name, ext = parseUri(git_uri)
        to = f'{self._tempdir}/{name}'
        if uri.scheme == 'https' and ext in ['', '.git']:
            if not self._skip_clone:
                rm_rf(to)
                mkdir_p(to)
                run(f'git clone {git_uri} {to}')
                run(f'git fetch --all --tags', cwd=to)
            return to
        elif (uri.scheme == 'file' or uri.scheme == '') and ext == '':
            return uri.path
        else:
            die('Cannot determine git repo - aborting.')

    def _get_docs(self, branch: str, content: dict) -> None:
        docs = self.get('docs')
        self._docs_repo = self._git_clone(docs)
        logging.info(f'Copying {self.get("type")} {branch}/docs')
        run(f'git checkout {branch}', cwd=self._docs_repo)
        rsync(f'{self._docs_repo}/docs/', f'{content}/docs')

    def _get_commands(self, content: str, commands: dict, core: bool = False) -> dict:
        docs = self.get('docs')
        dev_branch = docs.get('dev_branch')
        run(f'git checkout {dev_branch}', cwd=self._docs_repo)

        filename = self.get("docs").get("commands")
        filepath = f'{self._docs_repo}/{filename}'
        logging.info(
            f'Reading {self.get("type")} commands.json from {dev_branch}/{filename}')

        cmds = load_dict(filepath)

        sinter = set(cmds).intersection(set(commands))
        if len(sinter) != 0:
            logging.error(f'Duplicate commands found in {self._id}:')
            logging.error(sinter)
            die()
        else:
            commands.update(cmds)

        dst = f'{content}/commands/'
        for cmd in cmds.keys():
            filename = command_filename(cmd)
            rsync(f'{self._docs_repo}/commands/{filename}.md', dst)
        if core:
            rsync(f'{self._docs_repo}/commands/_index.md', dst)

    def _persist_commands(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("commands")}'
        logging.info(f'Persisting commands: {filepath}')
        dump_dict(filepath, self._commands)

    def _persist_groups(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("groups")}'
        logging.info(f'Persisting groups: {filepath}')
        dump_dict(filepath, self._groups)

    def _process_commands(self, content) -> None:
        for name in self._commands:
            md_path = f'{content}/commands/{command_filename(name)}.md'
            md = Markdown(md_path)
            md.process_command(name, self._commands)

    def _apply_stack(self) -> None:
        self._groups = OrderedDict()
        self._commands = OrderedDict()
        self._website = self.get('website')

        content_path = f'{self._website.get("path")}/{self._website.get("content")}'
        rm_rf(content_path)
        mkdir_p(content_path)

        components = self.get('components')
        for component in components:
            if type(component) == str:
                _, ext = os.path.splitext(component)
                if ext == '':
                    component += self._ext
                c = Component(filepath=f'{self._dirname}/{component}',
                              skip_clone=self._skip_clone, tempdir=self._tempdir)
            elif type(component) == dict:
                c = Component(component)
            else:
                die(f'Unknown component definition for {component}')
            c.apply(content=content_path, groups=self._groups,
                    commands=self._commands)

        self._persist_commands()
        self._persist_groups()
        self._process_commands(content_path)

    def _apply_core(self, content: str, groups: dict, commands: dict) -> None:
        docs = self.get('docs')
        dev_branch = docs.get('dev_branch')
        self._get_docs(dev_branch, content)
        self._get_commands(content, commands, core=True)

    def _apply_docs(self, content: str) -> None:
        pass

    def _apply_module(self, content: str, groups: dict, commands: dict) -> None:
        pass

    def apply(self, **kwargs):
        _type = self.get('type')
        name = self.get('name')
        content = kwargs.pop('content', dict)
        groups = kwargs.pop('groups', dict)
        commands = kwargs.pop('commands', dict)
        logging.info(f'Applying {_type} {name}')
        if _type == 'core':
            self._apply_core(content, groups, commands, **kwargs)
        elif _type == 'module':
            self._apply_module(content, groups, commands, **kwargs)
        elif _type == 'docs':
            self._apply_docs(content, **kwargs)
        elif _type == 'stack':
            self._apply_stack()
        else:
            die(f'Unknown component type: {_type} - aborting.')


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
    STACK = Component(
        filepath=ARGS.stack, skip_clone=ARGS.skip_clone, tempdir=ARGS.tempdir)

    # Make the stack
    STACK.apply()

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
