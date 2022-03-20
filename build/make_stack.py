import argparse
from calendar import c
from contextlib import contextmanager
from ctypes import resize
from curses.ascii import isdigit
from datetime import datetime
import errno
from genericpath import isfile
from importlib.resources import path
import io
import json
import requests
from xml.dom.expatbuilder import theDOMImplementation
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


class Repository(dict):
    def __init__(self, uri):
        super().__init__()
        self.uri = urlparse(f'https://{uri}')
        self.owner, self.name = os.path.split(self.uri.path)
        self.owner = self.owner[1:]
        self._get_gh_stats()
    def _get_gh_stats(self) -> None:
        if self.uri.netloc != 'github.com':
            return
        r = requests.get(
            f'https://api.github.com/repos/{self.owner}/{self.name}')
        j = r.json()
        for prop in ['archived', 'license', 'created_at', 'pushed_at', 'description', 'homepage', 'forks_count', 'stargazers_count', 'open_issues_count', ]:
            self[prop] = j.get(prop, None)


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

    def __init__(self, filepath: str = None):
        self.filepath = filepath
        self.fm_type = None
        self.fm_ext = None
        self.fm_data = dict()
        if not self.filepath:
            return
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

    def report_links(self):
        links = re.findall(r'(\[.+\])(\(.+\))', self.payload)
        exc = ['./', '#', '/commands', '/community', '/docs', '/topics']
        for link in links:
            ex = False
            for e in exc:
                if link[1].startswith(f'({e}'):
                    ex = True
                    break
            if not ex:
                print(f'"{link[1]}","{link[0]}","{self.filepath}"')

    def persist(self):
        # self.report_links()
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
            exclude = set([name])
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

    @staticmethod
    def convert_reply_shortcuts(payload):
        """ Convert RESP2 reply type shortcuts to links """
        def reply(x):
            resp2 = {
                'nil': ('resp-bulk-strings', 'Null reply'),
                'simple-string': ('resp-simple-string', 'Simple string reply'),
                'integer': ('resp-integers', 'Integer reply'),
                'bulk-string': ('resp-bulk-strings', 'Bulk string reply'),
                'array': ('resp-arrays', 'Array reply'),
                'error': ('resp-errors', 'Error reply'),

            }
            rep = resp2.get(x.group(1), None)
            if rep:
                return f'[{rep[1]}](/docs/reference/protocol-spec/#{rep[0]})'
            return f'[]'

        rep = re.sub(r'@(.+)-reply',
                     reply, payload)
        return rep

    @staticmethod
    def convert_command_sections(payload):
        """ Converts redis-doc section headers to MD """
        rep = re.sub(r'@examples\n',
                     '### Examples\n', payload)
        rep = re.sub(r'@return\n',
                     '### Return\n', rep)
        return rep

    def add_command_frontmatter(self, name, commands):
        """ Sets a JSON FrontMatter payload for a command page """
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
        """ New command processing logic """
        logging.debug(f'Processing command {self.filepath}')
        self.payload = self.generate_commands_links(
            name, commands, self.payload)
        self.payload = self.convert_command_sections(self.payload)
        self.payload = self.convert_reply_shortcuts(self.payload)
        self.payload = self.convert_cli_snippets(self.payload)
        self.add_command_frontmatter(name, commands)
        self.persist()

    def process_doc(self, commands):
        """ New doc processing logic """
        logging.debug(f'Processing document {self.filepath}')
        self.payload = self.generate_commands_links(
            None, commands, self.payload)
        self.persist()

    def patch_module_paths(self, module: dict) -> None:
        """ Replaces absolute module documentation links """
        def rep(x):
            if x.group(2).startswith(f'(/{_id}'):
                r = f'{x.group(1)}({x.group(2)[len(_id)+3:-1]})'
                return r
            else:
                return x.group(0)

        _id = module.get('id')
        self.payload = re.sub(f'(\[.+\])(\(.+\))', rep, self.payload)


class Component(dict):
    def __init__(self, filepath: str, clones: list, **kwargs):
        super().__init__()
        if filepath:
            self._uri, self._dirname, self._filename, self._ext = parseUri(
                filepath)
            self.update(load_dict(filepath))
        self._clones = clones
        self._id = self.get('id')
        self._type = self.get('type')
        self._name = self.get('name', self._id)
        self._desc = self.get('description', '')
        self._stack_path = self.get('stack_path', '')
        self._repository = self.get('repository', None)
        self._docs = self.get('docs', None)
        self._commands = self.get('commands', None)
        self._misc = self.get('misc', None)
        self._skip_clone = kwargs.get('skip_clone')
        self._get_stats = kwargs.get('get_stats')
        self._tempdir = f'{kwargs.get("tempdir")}/{self.get("id")}'

    @staticmethod
    def _dump_payload(spath: str, dpath: str, payload: list) -> None:
        if not payload:
            return
        for dump in payload:
            src = dump.get('src')
            dst = dump.get('dst', src)
            s = f'{spath}/{src}'
            d = f'{dpath}/{dst}'
            if os.path.isfile(s):
                mkdir_p(os.path.dirname(d))
            else:
                mkdir_p(d)
            rsync(s, d)
            search = dump.get('search', None)
            replace = dump.get('replace', None)
            if search:
                if os.path.isdir(s):
                    files = next(os.walk(d), (None, None, []))[2]
                else:
                    files = [d]
                for file in files:
                    regex_in_file(file, search, replace)

    @staticmethod
    def _get_dev_branch(repository: dict) -> str:
        branch = repository.get("dev_branch")
        post = repository .get("branches_postfix", "")
        return f'{branch}{post}'

    def _git_clone(self, repo) -> str:
        git_uri = repo.get('git_uri')
        private = repo.get('private', False)
        uri, _, name, ext = parseUri(git_uri)
        to = f'{self._tempdir}/{name}'
        if uri.scheme == 'https' and ext in ['', '.git']:
            if not self._skip_clone and git_uri not in self._clones:
                rm_rf(to)
                mkdir_p(to)
                logging.debug(
                    f'Cloning {private and "private" or "public"} {git_uri} to {to}')
                if private:
                    pat = os.environ.get('PRIVATE_REPOS_PAT')
                    if pat is None:
                        die('Private repos without a PAT - aborting.')
                    git_uri = f'{uri.scheme}://{pat}@{uri.netloc}{uri.path}'
                run(f'git clone {git_uri} {to}')
                run(f'git fetch --all --tags', cwd=to)
                self._clones.append(to)
            else:
                logging.debug(f'Skipping clone {git_uri}')
            return to
        elif (uri.scheme == 'file' or uri.scheme == '') and ext == '':
            return uri.path
        else:
            die('Cannot determine git repo - aborting.')

    def _get_docs(self, content: dict, stack: str = '') -> None:
        docs = self._docs
        repo = self._git_clone(docs)
        branch = Component._get_dev_branch(docs)
        run(f'git checkout {branch}', cwd=repo)
        path = docs.get('path', '')
        stack_path = f'{stack}/{self.get("stack_path", "")}'
        logging.info(f'Copying docs')
        src = f'{repo}/{path}/'
        dst = f'{content}/docs/{stack_path}'
        mkdir_p(dst)
        rsync(src, dst)
        Component._dump_payload(src, dst, docs.get('payload', None))

        # if self.get('type') == 'module':
        #     files = [f'{dst}/{f}' for f in ['index.md', '_index.md']]
        #     l = len(files)
        #     while l > 0:
        #         f = files.pop(0)
        #         l -= 1
        #         if os.path.isfile(f):
        #             files.append(f)
        #     if len(files) == 0:
        #         logging.warning(
        #             f'no index.md nor _index.md found in {dst} - please rectify the situation stat!!')
        #     if len(files) > 1:
        #         logging.warning(
        #             f'both index.md and _index.md exist in {dst} - please address this immediately!!!')

        #     stack_weight = self.get('stack_weight')
        #     for f in files:
        #         md = Markdown(f)
        #         md.fm_data['weight'] = stack_weight
        #         md.persist()

        #     files = run(f'find {dst} -regex ".*\.md"').strip().split('\n')
        #     for f in files:
        #         md = Markdown(f)
        #         t = md.fm_data.pop('type', None)
        #         if t:
        #             logging.warning(
        #                 f'the file {f} has a type set to `{t}` - please prevent future harm by acting now, thank you.')
        #         md.patch_module_paths(self)
        #         md.persist()

    def _get_commands(self, content: str, commands: dict) -> dict:
        repo = self._git_clone(self._commands)
        branch = Component._get_dev_branch(self._commands)
        run(f'git checkout {branch}', cwd=repo)
        path = self._commands.get('path', '')

        logging.info(f'Copying commands')
        filename = self._commands.get('defs', 'commands.json')
        filepath = f'{repo}/{filename}'
        logging.info(
            f'Reading {self._type} commands.json from {branch}/{filename}')
        cmds = load_dict(filepath)

        sinter = set(cmds).intersection(set(commands))
        if len(sinter) != 0:
            logging.error(f'Duplicate command(s) found in {self._id}:')
            logging.error(sinter)
            die()
        else:
            commands.update(cmds)

        base = f'{repo}/{path}/'
        dst = f'{content}/commands/'
        srcs = [f'{base}{command_filename(cmd)}.md' for cmd in cmds.keys()]
        rsync(' '.join(srcs), dst)
        Component._dump_payload(base, dst, self._commands.get('payload', None))

    def _make_group(self, data: dict = {}) -> None:
        d = {
            'type': self.get('type'),
            'display': data.get('display', self.get('id')),
            'description': data.get('description', self._desc),
            'weight': self.get('stack_weight', 0)
        }
        return d

    def _get_groups(self, groups: dict) -> None:
        repo = self._git_clone(self._commands)
        branch = Component._get_dev_branch(self._commands)
        run(f'git checkout {branch}', cwd=repo)
        logging.info(f'Getting groups')
        filename = self._commands.get('groups', 'groups.json')
        filepath = f'{repo}/{filename}'
        logging.info(
            f'Reading {self._type} groups.json from {branch}/{filename}')
        g = load_dict(filepath)
        g = {group: self._make_group(data) for (group, data) in g.items()}
        groups.update(g)

    @staticmethod
    def _make_data(path: str) -> dict:
        data = {}
        for root, _, files in os.walk(path, topdown=False):
            for filename in files:
                fullpath = os.path.join(root, filename)
                name, _ = os.path.splitext(filename)
                s = root[len(path)+1:].split('/')
                key, domain = s[0], s[1]
                if len(s) > 2:
                    org = f'{s[2]}/'
                else:
                    org = ''
                d = load_dict(fullpath)
                field = d.pop('name')
                d.update({
                    'repository': f'{domain}/{org}{name}',
                })
                if key not in data:
                    data.update({
                        key: {}
                    })
                data.get(key).update({
                    field: d
                })
        return data

    def _get_data(self) -> None:
        data = self.get('data')
        repo = self._git_clone(data)
        branch = Component._get_dev_branch(data)
        run(f'git checkout {branch}', cwd=repo)
        logging.info(f'Getting data')
        for src in ['languages', 'tool_types']:
            filename = data.get(src)
            filepath = f'{repo}/{filename}'
            rsync(filepath, 'data/')
        repos = {}
        for src in ['clients', 'libraries', 'modules', 'tools']:
            data = Component._make_data(f'{repo}/{src}')
            repos[src] = data
        if self._get_stats:
            for cat, subs in repos.items():
                for sub, rs in subs.items():
                    for n, d in rs.items():
                        logging.info(f'Getting stats for {n}')
                        r = Repository(d.get('repository'))
                        repos[cat][sub][n].update(dict(r))
        dump_dict(f'data/repos.json', repos)

    def _get_misc(self, content) -> None:
        repo = self._git_clone(self._misc)
        branch = Component._get_dev_branch(self._misc)
        run(f'git checkout {branch}', cwd=repo)
        Component._dump_payload(
            repo, f'{content}/{self._stack_path}', self._misc.get('payload'))

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
        out = run(
            f'find {content} -type f -name "*.md" | grep -ive "{content}/commands"').strip().split('\n')
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
                c = Component(f'{self._dirname}/{component}', self._clones,
                              skip_clone=self._skip_clone, get_stats=self._get_stats,
                              tempdir=self._tempdir)
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
        self._get_docs(content)
        self._get_commands(content, commands)
        self._get_groups(groups)
        self._get_misc(content)
        self._get_data()

    def _apply_docs(self, content: str) -> None:
        self._get_docs(content)
        self._get_misc(content)

    def _apply_module(self, content: str, stack: str, groups: dict, commands: dict) -> None:
        self._get_docs(content, stack)
        self._get_commands(content, commands)
        groups.update({self._id: self._make_group()})

    def _apply_asset(self) -> None:
        if not self._repository:
            return
        repo = self._git_clone(self._repository)
        dev_branch = self._repository.get('dev_branch')
        run(f'git checkout {dev_branch}', cwd=repo)
        Component._dump_payload(repo, './', self._repository.get('payload'))

    def apply(self, **kwargs):
        content = kwargs.pop('content', dict)
        stack = kwargs.pop('stack', dict)
        groups = kwargs.pop('groups', dict)
        commands = kwargs.pop('commands', dict)
        logging.info(f'Applying {self._type}: {self._name}')
        if self._type == 'core':
            self._apply_core(content, groups, commands, **kwargs)
        elif self._type == 'module':
            self._apply_module(content, stack, groups, commands, **kwargs)
        elif self._type == 'docs':
            self._apply_docs(content, **kwargs)
        elif self._type == 'asset':
            self._apply_asset(**kwargs)
        elif self._type == 'stack':
            self._apply_stack()
        else:
            die(f'Unknown component type: {self._type} - aborting.')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Builds a stack website')
    parser.add_argument('--stack', type=str,
                        default='./data/stack.json',
                        help='path to stack definition')
    parser.add_argument('--skip-clone', action='store_true',
                        help='skips `git clone`')
    parser.add_argument('--get-stats', action='store_true',
                        help='Attempts scraping the internet for statistics')
    parser.add_argument('--loglevel', type=str,
                        default='INFO',
                        help='Python logging level (overwrites LOGLEVEL env var)')
    parser.add_argument('--tempdir', type=str,
                        help='temporary path', default=f'{tempfile.gettempdir()}')
    return parser.parse_args()


if __name__ == '__main__':
    # Init
    ARGS = parse_args()
    mkdir_p(ARGS.tempdir)

    # Load settings
    STACK = Component(ARGS.stack, [], **ARGS.__dict__)

    # Make the stack
    logging.basicConfig(
        level=ARGS.loglevel, format='%(filename)s: %(levelname)s %(asctime)s %(message)s')
    print(f'APPLY STACK "{STACK._name}"')
    start = datetime.now()
    STACK.apply()
    total = datetime.now() - start
    print(f'+OK ({total.microseconds / 1000} ms)')
