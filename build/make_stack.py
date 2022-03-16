import argparse
from ast import Str
from calendar import c
from contextlib import contextmanager
import errno
import io
import json
from operator import mod
from pydoc import stripid
from statistics import fmean
import yaml
import pytoml
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from textwrap import TextWrapper
from typing import Any, AnyStr, OrderedDict, Tuple
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
    cmd = f'rsync -av --no-owner --no-group --exclude={{{",".join(ex)}}} {src} {dst}'
    return run(cmd)


def log_func(args: list) -> None:
    caller = sys._getframe(1).f_code.co_name
    logging.debug('called %s(%s)', caller, args)


def log_dict(msg, obj, *props):
    d = {prop: obj.get(prop, None) for prop in props}
    logging.info(f'{msg} {d}')


def parseUri(uri: str) -> Tuple[ParseResult, str, str]:
    _uri = urlparse(uri)
    dirname = os.path.dirname(ARGS.stack)
    _, name = os.path.split(_uri.path)
    _, ext = os.path.splitext(name)
    return _uri, dirname, name, ext


# def filter_by_res(elems: list, include: str, exclude: list) -> list:
#     log_func(locals())
#     e = [re.match(include, elem) for elem in elems]
#     e = [elem[1] for elem in e if elem]
#     for ex in exclude:
#         e = [x for x in e if not re.match(ex, x)]
#     e.sort(reverse=True)
#     return e


# def get_tags(repo_path: str, res: dict) -> list:
#     tags = do_or_die(['git', 'tag'], cwd=repo_path).split('\n')
#     tags = filter_by_res(tags, res.get('include_tag_regex'),
#                          res.get('exclude_tag_regexes'))
#     return tags


# def get_branches(repo_path: str, res: dict) -> list:
#     branches = do_or_die(['git', 'branch', '-r'], cwd=repo_path).split('\n')
#     branches = [branch.strip() for branch in branches]
#     branches = filter_by_res(branches, f'origin/({res.get("include_branch_regex")})',
#                              [f'origin/({bre})' for bre in res.get('exclude_branch_regexes')])
#     return branches


# def get_dev_docs(website: dict, piece: dict, piece_path: str, commands: dict) -> dict:
#     rels = piece.get('releases', None)
#     rels_repo = f'{piece_path}/rels_repo'
#     if type(rels) is dict:
#         source = rels.get('source', None)
#         if source not in piece:
#             logging.error(
#                 f'Invalid releases source key for {id} - aborting.')
#         if source == 'docs':
#             rels_repo = docs_repo
#         elif source == 'repository':
#             git_get(piece.get(source).get(
#                 'git_uri'), rels_repo, args.skip_clone)

#     if rels:
#         tags = []
#         if rels.get('tags', False):
#             tags = get_tags(rels_repo, rels)
#         branches = get_branches(rels_repo, rels)

#     for (s, d) in payload:
#         do_or_die(['rsync', '-av', '--no-owner', '--no-group', s, d])

#     return commands


# ------------------------------------------------------------------------------
def command_filename(name: str) -> str:
    return name.lower().replace(' ', '-')


def regex_in_file(path: str, search: str, replace: str):
    with open(path, 'r') as f:
        p = f.read()
    r = re.compile(search)
    p = r.sub(replace, p)
    with open(path, 'w') as f:
        f.write(p)


class StructuredData:
    PARSERS = {
        '.json': {
            'dump': lambda x, y: json.dump(x, y, indent=4),
            'dumps': lambda x: json.dumps(x, indent=4),
            'load': lambda x: json.load(x),
            'loads': lambda x: json.loads(x),
        },
        '.yaml': {
            'dump': lambda x, y: yaml.dump(x, y),
            'dumps': lambda x: yaml.dump(x),
            'load': lambda x: yaml.load(x, Loader=yaml.FullLoader),
            'loads': lambda x: yaml.load(io.StringIO(x), Loader=yaml.FullLoader),
        },
        '.toml': {
            'dump': lambda x, y: pytoml.dump(x, y),
            'dumps': lambda x: pytoml.dumps(x),
            'load': lambda x: pytoml.load(x),
            'loads': lambda x: pytoml.loads(x),
        },
    }

    def __init__(self):
        pass

    @staticmethod
    def dump(ext: str, d: dict, f: Any) -> None:
        if ext in StructuredData.PARSERS:
            return StructuredData.PARSERS.get(ext).get('dump')(d, f)
        else:
            raise RuntimeError(f'unknown extension {ext}')

    @staticmethod
    def dumps(ext: str, d: dict) -> None:
        if ext in StructuredData.PARSERS:
            return StructuredData.PARSERS.get(ext).get('dumps')(d)
        else:
            raise RuntimeError(f'unknown extension {ext}')

    @staticmethod
    def load(ext: str, f: Any) -> dict:
        if ext in StructuredData.PARSERS:
            return StructuredData.PARSERS.get(ext).get('load')(f)
        else:
            raise RuntimeError(f'unknown extension {ext}')

    @staticmethod
    def loads(ext: str, s: str) -> dict:
        if ext in StructuredData.PARSERS:
            return StructuredData.PARSERS.get(ext).get('loads')(s)
        else:
            raise RuntimeError(f'unknown extension {ext}')


def load_dict(filepath: str) -> dict:
    # _, name = os.path.split(filepath)
    _, ext = os.path.splitext(filepath)
    with open(filepath, 'r') as f:
        o = StructuredData.load(ext, f)
    return o


def dump_dict(filepath: str, d: dict) -> None:
    _, ext = os.path.splitext(filepath)
    with open(filepath, 'w') as f:
        StructuredData.dump(ext, d, f)


class Markdown:
    FM_TYPES = {
        '{\n': {
            'eof': '}\n',
            'ext': '.json'
        },
        '---\n': {
            'eof': '---\n',
            'ext': '.yaml'
        },
        '+++\n': {
            'eof': '+++\n',
            'ext': '.toml'
        }
    }

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.fm_type = None
        self.fm_ext = None
        self.fm_data = dict()
        with open(self.filepath, 'r') as f:
            payload = f.readlines()
        if not len(payload):
            self.payload = ''
            return
        i = 0
        while i < len(payload):             # Munch newlines
            if payload[i].strip() == '':
                i += 1
            else:
                break
        if payload[i].startswith('\ufeff'):  # BOM workaround
            payload[i] = payload[i][1:]

        self.fm_type = self.FM_TYPES.get(payload[i])
        if not self.fm_type:
            self.payload = ''.join(payload)
            return
        eof, self.fm_ext = self.fm_type.get('eof'), self.fm_type.get('ext')
        found = False
        for j in range(i+1, len(payload)):
            if payload[j] == eof:
                found = True
                break
        if not found and payload[j].strip() != eof.strip():
            die(f'No eof for frontmatter: {payload}')
        if self.fm_ext == '.json':
            self.fm_data.update(StructuredData.loads(
                self.fm_ext, ''.join(payload[i:j+1])))
            self.payload = ''.join(payload[j+1:])
        else:
            self.fm_data.update(StructuredData.loads(
                self.fm_ext, ''.join(payload[i+1:j])))
            self.payload = ''.join(payload[j+1:])

    def persist(self):
        payload = self.payload
        if self.fm_type:
            fm = StructuredData.dumps(self.fm_ext, self.fm_data)
            if self.fm_ext != '.json':
                fm = f'{self.fm_type.get("eof")}{fm}{self.fm_type.get("eof")}'
            else:
                fm += '\n'
            payload = fm + payload
        else:
            logging.warning(
                f'{self.filepath} has no FrontMatter attached - please make a corrective move ASAP!')

        with open(self.filepath, 'w') as f:
            f.write(payload)

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
    def make_command_linkifier(commands: dict, name: str):
        """
        Returns a function (for re.sub) that converts valid ticked command names to
        markdown links. This excludes the command in the context, as well as any of
        its arguments' tokens.
        """
        if name:
            exclude = set(name)
            tokens = Markdown.get_command_tokens(commands.get(name))
            exclude.union(tokens)
        else:
            exclude = set()

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
        linkifier = Markdown.make_command_linkifier(commands, name)
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
        rep = re.sub(r'```cli\n(.*)\n```\n',
                     Markdown.get_cli_shortcode, payload, flags=re.S)
        return rep

    def add_command_frontmatter(self, name, commands):
        data = commands.get(name)
        data.update({
            'title': name,
            'linkTitle': name,
            'description': data.get('summary')
        })
        if 'replaced_by' in data:
            data['replaced_by'] = self.generate_commands_links(
                name, commands, data.get('replaced_by'))
        self.fm_type = self.FM_TYPES.get('{\n')
        self.fm_ext = self.fm_type.get('ext')
        self.fm_data.update(data)

    def process_command(self, name, commands):
        logging.debug(f'Processing command {self.filepath}')
        self.payload = self.generate_commands_links(
            name, commands, self.payload)
        self.payload = self.convert_cli_snippets(self.payload)
        self.add_command_frontmatter(name, commands)
        self.persist()

    def process_doc(self, commands):
        logging.debug(f'Processing document {self.filepath}')
        self.payload = self.generate_commands_links(
            None, commands, self.payload)
        self.persist()

    def patch_module_paths(self, module: dict, stack_path) -> None:
        _id = module.get('id')
        self.payload = re.sub(f'(\[.+\])(\(.+\))',
                              lambda x: (
                                  x.group(2).startswith(f'(/{_id}')
                                  and f'{x.group(1)}({stack_path}{x.group(2)[len(_id)+2:-1]})'
                              ) or x.group(0), self.payload)


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
        private = repo.get('private', False)
        uri, _, name, ext = parseUri(git_uri)
        to = f'{self._tempdir}/{name}'
        if uri.scheme == 'https' and ext in ['', '.git']:
            if not self._skip_clone:
                rm_rf(to)
                mkdir_p(to)
                if private:
                    pat = os.environ.get('PRIVATE_REPOS_PAT')
                    if pat is None:
                        die('Private repos without a PAT - aborting.')
                    git_uri = f'{uri.scheme}://{pat}@{uri.netloc}{uri.path}'
                run(f'git clone {git_uri} {to}')
                run(f'git fetch --all --tags', cwd=to)
            return to
        elif (uri.scheme == 'file' or uri.scheme == '') and ext == '':
            return uri.path
        else:
            die('Cannot determine git repo - aborting.')

    def _docs_dev_branch(self) -> str:
        return f'{self.get("docs").get("dev_branch")}{self.get("docs").get("branches_postfix","")}'

    def _get_docs(self, branch: str, content: dict, stack: str = '') -> None:
        docs = self.get('docs')
        self._docs_repo = self._git_clone(docs)
        run(f'git checkout {branch}', cwd=self._docs_repo)
        path = docs.get('path', '')
        stack_path = f'{stack}/{self.get("stack_path", "")}'
        logging.info(f'Copying docs')

        ex = ['.*']
        if self.get('type') in ['core', 'docs']:
            ex += docs.get('exclude', [])
            ex += ['README.md', 'groups.json',
                   'commands.json', '/commands', '/docs']
            src = f'{self._docs_repo}/{path}/'
            rsync(src, content, exclude=ex)

        src = f'{self._docs_repo}/{path}/docs/'
        dst = f'{content}/docs/{stack_path}'
        mkdir_p(dst)
        rsync(src, dst)

        if self.get('type') == 'module':
            files = [f'{dst}/{f}' for f in ['index.md', '_index.md']]
            l = len(files)
            while l > 0:
                f = files.pop(0)
                l -= 1
                if os.path.isfile(f):
                    files.append(f)
            if len(files) == 0:
                logging.warning(
                    f'no index.md nor _index.md found in {dst} - please rectify the situation stat!!')
            if len(files) > 1:
                logging.warning(
                    f'both index.md and _index.md exist in {dst} - please address this immediately!!!')

            stack_weight = self.get('stack_weight')
            for f in files:
                md = Markdown(f)
                md.fm_data['weight'] = stack_weight
                md.persist()

            files = run(f'find {dst} -regex ".*\.md"').strip().split('\n')
            for f in files:
                md = Markdown(f)
                t = md.fm_data.pop('type', None)
                if t:
                    logging.warning(
                        f'the file {f} has a type set to `{t}` - please prevent future harm by acting now, thank you.')
                md.patch_module_paths(self, f'/docs/{stack_path}')
                md.persist()

    def _get_commands(self, content: str, commands: dict) -> dict:
        run(f'git checkout {self._docs_dev_branch()}', cwd=self._docs_repo)
        docs = self.get('docs')
        filename = self.get('docs').get('commands', 'commands.json')
        filepath = f'{self._docs_repo}/{filename}'
        logging.info(
            f'Reading {self.get("type")} commands.json from {self._docs_dev_branch()}/{filename}')

        cmds = load_dict(filepath)

        sinter = set(cmds).intersection(set(commands))
        if len(sinter) != 0:
            logging.error(f'Duplicate commands found in {self._id}:')
            logging.error(sinter)
            die()
        else:
            commands.update(cmds)

        path = docs.get('path', '')
        base = f'{self._docs_repo}/{path}/commands/'
        dst = f'{content}/commands/'
        srcs = [f'{base}{command_filename(cmd)}.md' for cmd in cmds.keys()]
        if self.get('type') == 'core':
            srcs.append(f'{base}/_index.md')
        rsync(' '.join(srcs), dst)

    def _get_groups(self, groups: dict) -> None:
        run(f'git checkout {self._docs_dev_branch()}', cwd=self._docs_repo)
        g = load_dict(f'{self._docs_repo}/groups.json')
        groups.update(g)

    def _persist_commands(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("commands")}'
        logging.info(f'Persisting commands: {filepath}')
        dump_dict(filepath, self._commands)

    def _persist_groups(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("groups")}'
        logging.info(f'Persisting groups: {filepath}')
        dump_dict(filepath, self._groups)

    def _process_commands(self, content) -> None:
        logging.info(f'Processing commands')
        for name in self._commands:
            md_path = f'{content}/commands/{command_filename(name)}.md'
            md = Markdown(md_path)
            md.process_command(name, self._commands)

    def _process_docs(self, content) -> None:
        logging.info(f'Processing docs')
        out = run(f'find {content} -regex ".*\.md"').strip().split('\n')
        for md_path in out:
            md = Markdown(md_path)
            md.process_doc(self._commands)

    def _apply_stack(self) -> None:
        self._groups = OrderedDict()
        self._commands = OrderedDict()
        self._website = self.get('website')
        self._stack_path = self.get('stack_path')

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
            c.apply(content=content_path, stack=self._stack_path, groups=self._groups,
                    commands=self._commands)

        self._persist_commands()
        self._persist_groups()
        self._process_commands(content_path)
        self._process_docs(content_path)

    def _apply_core(self, content: str, groups: dict, commands: dict) -> None:
        self._get_docs(self._docs_dev_branch(), content)
        self._get_commands(content, commands)
        self._get_groups(groups)

    def _apply_docs(self, content: str) -> None:
        self._get_docs(self._docs_dev_branch(), content)

    def _apply_module(self, content: str, stack: str, groups: dict, commands: dict) -> None:
        self._get_docs(self._docs_dev_branch(), content, stack)
        self._get_commands(content, commands)
        groups.update({
            self.get('id'): {
                'type': 'module',
                'display': self.get('name'),
                'description': self.get('description'),
            }
        })

    def _apply_asset(self) -> None:
        repository = self.get('repository')
        repo = self._git_clone(repository)
        dev_branch = repository.get('dev_branch')
        run(f'git checkout {dev_branch}', cwd=repo)
        payload = self.get('payload')
        logging.info(f'Dumping payload')
        for dump in payload:
            src = dump.get('src')
            dst = dump.get('dst', src)
            mkdir_p(dst)
            rsync(f'{repo}/{src}', dst)
            search, replace = dump.get(
                'search', None), dump.get('replace', None)
            if search:
                _, filename = os.path.split(src)
                path = f'{dst}/{filename}'
                regex_in_file(path, search, replace)

    def apply(self, **kwargs):
        _type = self.get('type')
        name = self.get('name')
        content = kwargs.pop('content', dict)
        stack = kwargs.pop('stack', dict)
        groups = kwargs.pop('groups', dict)
        commands = kwargs.pop('commands', dict)
        logging.info(f'Applying {_type} {name}')
        if _type == 'core':
            self._apply_core(content, groups, commands, **kwargs)
        elif _type == 'module':
            self._apply_module(content, stack, groups, commands, **kwargs)
        elif _type == 'docs':
            self._apply_docs(content, **kwargs)
        elif _type == 'asset':
            self._apply_asset(**kwargs)
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
