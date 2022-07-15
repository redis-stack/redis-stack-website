from ast import dump
from email.mime import base
import logging
import os
import semver
from typing import Tuple
from urllib.parse import urlparse, ParseResult

from .markdown import Markdown
from .structured_data import load_dict, dump_dict
from .syntax import Command
from .util import die, mkdir_p, rsync, regex_in_file, run, rm_rf, command_filename, slugify


def parseUri(uri: str) -> Tuple[ParseResult, str, str]:
    _uri = urlparse(uri)
    dirname = os.path.dirname(uri)
    _, name = os.path.split(_uri.path)
    _, ext = os.path.splitext(name)
    return _uri, dirname, name, ext


class Component(dict):
    def __init__(self, filepath: str = None, root: dict = None, args: dict = None):
        super().__init__()
        self._root = root
        self._args = args
        if filepath:
            self._uri, self._dirname, self._filename, self._ext = parseUri(
                filepath)
            self.update(load_dict(filepath))
        self._id = self.get('id')
        self._type = self.get('type')
        self._name = self.get('name', self._id)
        self._desc = self.get('description', '')
        self._stack_path = self.get('stack_path', '')
        self._repository = self.get('repository', None)
        self._env_prefix = self.get('env_prefix','')

    @staticmethod
    def _dump_payload(spath: str, dpath: str, payload: list) -> None:
        if not payload:
            return []
        files = []
        for dump in payload:
            src = dump.get('src')
            dst = dump.get('dst', src)
            s = f'{spath}/{src}'
            d = f'{dpath}/{dst}'
            if os.path.isfile(s):
                mkdir_p(os.path.dirname(d))
            else:
                mkdir_p(d)
            files += rsync(s, d)
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

    @staticmethod
    def _add_meta_fm(repo: str, branch: str, base: str, path: str) -> None:
        _, dirs, files = next(os.walk(base))
        for d in dirs:
            Component._add_meta_fm(repo, branch, f'{base}/{d}', f'{path}/{d}')
        for f in files:
            if not f.endswith('.md'):
                continue
            md = Markdown(f'{base}/{f}')
            md.add_github_metadata(repo, branch, f'{path}/{f}')
            md.persist()

    def _git_clone(self, repo) -> str:
        git_uri = repo.get('git_uri')
        private = repo.get('private', False)
        uri, _, name, ext = parseUri(git_uri)
        to = f'{self._root._tempdir}/{name}'
        if uri.scheme == 'https' and ext in ['', '.git'] and self._repo_env_dir() == '':
            if not self._root._skip_clone and git_uri not in self._root._clones:
                rm_rf(to)
                mkdir_p(to)
                logging.debug(
                    f'Cloning {private and "private" or "public"} {git_uri} to {to}')
                self._root._clones[git_uri] = True
                if private:
                    pat = os.environ.get('PRIVATE_ACCESS_TOKEN')
                    if pat is None:
                        die('Private repos without a PRIVATE_ACCESS_TOKEN - aborting.')
                    git_uri = f'{uri.scheme}://{pat}@{uri.netloc}{uri.path}'
                run(f'git clone {git_uri} {to}')
                run(f'git fetch --all --tags', cwd=to)
            else:
                logging.debug(f'Skipping clone {git_uri}')
            return to
        elif self._repo_env_dir() != '':
            return self._repo_env_dir()
        elif (uri.scheme == 'file' or uri.scheme == '') and ext == '':
            return uri.path
        else:
            die('Cannot determine git repo - aborting.')

    def _get_commands(self) -> list:
        commands = self.get('commands')
        repo = self._git_clone(commands)
        branch = Component._get_dev_branch(commands)
        run(f'git checkout {branch}', cwd=repo)
        path = commands.get('path', '')

        logging.info(f'Copying {self._id} commands')
        filename = commands.get('defs', 'commands.json')
        filepath = f'{repo}/{filename}'
        logging.info(
            f'Reading {self._id} {self._type} commands.json from {branch}/{filename}')
        cmds = load_dict(filepath)

        sinter = set(cmds).intersection(set(self._root._commands))
        if len(sinter) != 0:
            logging.error(f'Duplicate command(s) found in {self._id}:')
            logging.error(sinter)
            die()

        for key in cmds:
            cmds[key]['module'] = self._type == 'module'
        self._root._commands.update(cmds)

        base = f'{repo}/{path}/'
        dst = f'{self._root._website.get("content")}/commands/'
        srcs = [f'{base}{command_filename(cmd)}.md' for cmd in cmds]
        files = rsync(' '.join(srcs), dst)[1:-5]
        self._dump_payload(base, dst, cmds.get('payload', None))
        self._add_meta_fm(commands.get('git_uri'), branch, dst, path)
        if self._type == 'module':
            for file in files:
                path = f'{dst}/{file}'
                md = Markdown(path)
                md.patch_module_paths(self._id, self._stack_path)
                md.persist()
        return files

    def _get_groups(self) -> None:
        for key, val in self.get('groups').items():
            d = {
                'display': val.get('display', self._name),
                'description': val.get('description', self._desc),
                'weight': self.get('stack_weight', 0)
            }
            if self._type == 'module':
                top = 'stack'
                vdt = {}
            else:
                top = 'core'
                vdt = []
            if not self._root._groups.get(top):
                self._root._groups[top] = {}
                self._root._versions[top] = vdt
            if self._type == 'module':
                self._root._versions[top][key] = []
            self._root._groups[top][key] = d

    def _get_docs(self) -> list:
        docs = self.get('docs')
        repo = self._git_clone(docs)
        branch = Component._get_dev_branch(docs)
        run(f'git checkout {branch}', cwd=repo)
        path = docs.get('path', '')
        logging.info(f'Copying {self._id} docs')
        src = f'{repo}/{path}/'
        dst = f'{self._content}'
        mkdir_p(dst)
        files = rsync(src, dst)[1:-5]
        Component._dump_payload(src, dst, docs.get('payload', None))
        Component._add_meta_fm(docs.get('git_uri'), branch, dst, path)
        return files

    def _get_misc(self) -> None:
        misc = self.get('misc')
        repo = self._git_clone(misc)
        branch = Component._get_dev_branch(misc)
        run(f'git checkout {branch}', cwd=repo)
        Component._dump_payload(repo, self._root._content, misc.get('payload'))
        return
    
    def _repo_env_dir(self) -> str:
        if os.getenv(f'{self._env_prefix}_DIR'):
            return os.getenv(f'{self._env_prefix}_DIR')
        return ''


class Stack(Component):
    def __init__(self, filepath: str, root: dict = None, args: dict = None):
        super().__init__(filepath, root, args)
        self._groups = {}
        self._commands = {}
        self._versions = {}
        self._clones = {}
        self._repos = {}
        self._tempdir = args.get('tempdir')
        self._website = self.get('website')
        self._skip_clone = self.get('skip_clone')
        self._content = f'{self._website.get("path")}/{self._website.get("content")}'
        mkdir_p(self._content)

    def _persist_commands(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("commands")}'
        logging.info(f'Persisting {self._id} commands: {filepath}')
        dump_dict(filepath, self._commands)

    def _persist_groups(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("groups")}'
        logging.info(f'Persisting {self._id} groups: {filepath}')
        dump_dict(filepath, self._groups)

    def _persist_versions(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("versions")}'
        logging.info(f'Persisting {self._id} versions: {filepath}')
        for cmd in self._commands.values():
            since = semver.parse_version_info(cmd.get('since'))
            since = f'{since.major}.{since.minor}'
            if not cmd.get('module'):
                vers = self._versions['core']
            else:
                vers = self._versions['stack'][cmd.get('group')]
            if since not in vers:
                vers.append(since)
                vers.sort(reverse=True)
        dump_dict(filepath, self._versions)

    def _make_repos(self) -> None:
        logging.info(f'Making {self._id} repositories')
        meta = load_dict(self.get('website').get('meta'))
        for kname, kind in self._repos.items():
            for gname, group in kind.items():
                path = f'{self._content}/docs/{kname}'
                mkdir_p(path)
                for pname, project in group.items():
                    filename = f'{path}/{slugify(gname)}_{slugify(pname)}.md'
                    md = Markdown(filename, True)
                    md.payload = ''
                    md.fm_data['recommended'] = False
                    md.fm_data.update(project)
                    md.fm_data.update({'title': pname})
                    md.fm_data.update({'group': gname})
                    md.fm_data.update({'kind': kname})
                    md.fm_data.update(meta.get(project.get('repository'), {}))
                    md.persist()
        dump_dict(f'data/repos.json', self._repos)

    def _process_commands(self) -> None:
        logging.info(f'Processing {self._id} commands')
        for name in self._commands:
            path = f'{self._content}/commands/{command_filename(name)}'
            mkdir_p(path)
            run(f'mv {path}.md {path}/index.md')
            md = Markdown(f'{path}/index.md')
            md.process_command(name, self._commands)
            c = Command(name, self._commands.get(name))
            d = c.diagram()
            with open(f'{path}/syntax.svg', 'w+') as f:
                f.write(d)

    def _process_docs(self) -> None:
        logging.info(f'Processing {self._id} docs')
        out = run(
            f'find {self._content} -type f -name "*.md" | grep -ive "{self._content}/commands"').strip().split('\n')
        for md_path in out:
            md = Markdown(md_path, True)
            md.process_doc(self._commands)

    def apply(self) -> None:
        for kind in ['core', 'docs', 'modules', 'assets']:
            for component in self.get(kind):
                if type(component) == str:
                    basename, ext = os.path.splitext(component)
                    if ext == '':
                        component += self._ext
                    filename = f'{self._dirname}/{component}'
                    if kind == 'core':
                        c = Core(filename, self)
                    elif kind == 'docs':
                        c = Docs(filename, self)
                    elif kind == 'modules':
                        if self._args.get('module') in ['*', basename]:
                            c = Module(filename, self)
                        else:
                            continue
                    elif kind == 'assets':
                        c = Asset(filename, self)
                else:
                    die(f'Unknown component definition for {component}')
                c.apply()
        self._persist_commands()
        self._persist_groups()
        self._persist_versions()
        self._process_commands()
        self._process_docs()
        self._make_repos()


class Core(Component):
    def __init__(self, filepath: str, root: dict = None):
        super().__init__(filepath, root)
        self._content = f'{self._root._content}/{self._stack_path}'

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
        logging.info(f'Getting {self._id} data')
        for src in ['languages', 'tool_types']:
            filename = data.get(src)
            filepath = f'{repo}/{filename}'
            rsync(filepath, 'data/')
        for src in ['clients', 'libraries', 'modules', 'tools']:
            data = self._make_data(f'{repo}/{src}')
            self._root._repos[src] = data

    def apply(self) -> None:
        logging.info(f'Applying core {self._id}')
        files = self._get_docs()
        files += self._get_commands()
        self._get_misc()
        self._get_groups()
        self._get_data()
        return files


class Docs(Component):
    def __init__(self, filepath: str, root: dict = None):
        super().__init__(filepath, root)
        self._content = f'{self._root._content}/{self._stack_path}'

    def apply(self) -> None:
        logging.info(f'Applying docs {self._id}')
        files = self._get_docs()
        self._get_misc()
        return files


class Module(Component):
    def __init__(self, filepath: str, root: dict = None):
        super().__init__(filepath, root)
        self._content = f'{self._root._content}/{self._stack_path}'

    def _process_module_docs(self, files: list) -> None:
        if self.get('type') == 'module':
            foes = [f'{self._content}/{f}' for f in ['index.md', '_index.md']]
            l = len(foes)
            while l > 0:
                f = foes.pop(0)
                l -= 1
                if os.path.isfile(f):
                    foes.append(f)
            if len(foes) == 0:
                logging.warning(
                    f'no index.md nor _index.md found in {self._content} - please rectify the situation stat!!')
            if len(foes) > 1:
                logging.warning(
                    f'both index.md and _index.md exist in {self._content} - please address this immediately!!!')

            stack_weight = self.get('stack_weight')
            for f in foes:
                md = Markdown(f)
                md.fm_data['weight'] = stack_weight
                md.persist()

            files = run(
                f'find {self._content} -regex ".*\.md"').strip().split('\n')
            for f in files:
                md = Markdown(f)
                t = md.fm_data.pop('type', None)
                if t:
                    logging.warning(
                        f'the file {f} has a type set to `{t}` - please prevent future harm by acting now, thank you.')
                md.patch_module_paths(self._id, self._stack_path)
                md.persist()

    def apply(self) -> None:
        logging.info(f'Applying module {self._id}')
        files = self._get_docs()
        self._process_module_docs(files)
        files += self._get_commands()
        self._get_groups()
        return files


class Asset(Component):
    def __init__(self, filepath: str, root: dict = None):
        super().__init__(filepath, root)

    def apply(self) -> None:
        logging.info(f'Applying asset {self._id}')
        if not self._repository:
            return
        repo = self._git_clone(self._repository)
        dev_branch = self._repository.get('dev_branch')
        run(f'git checkout {dev_branch}', cwd=repo)
        return Component._dump_payload(repo, './', self._repository.get('payload'))
