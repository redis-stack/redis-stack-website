import logging
import os
import semver
from typing import Tuple
from urllib.parse import urlparse, ParseResult
from github import Repository
from markdown import Markdown
from structured_data import load_dict, dump_dict
from util import die, mkdir_p, rsync, regex_in_file, run, rm_rf, command_filename


def parseUri(uri: str) -> Tuple[ParseResult, str, str]:
    _uri = urlparse(uri)
    dirname = os.path.dirname(uri)
    _, name = os.path.split(_uri.path)
    _, ext = os.path.splitext(name)
    return _uri, dirname, name, ext


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
        to = f'{self._tempdir}/{name}'
        if uri.scheme == 'https' and ext in ['', '.git']:
            if not self._skip_clone and git_uri not in self._clones:
                rm_rf(to)
                mkdir_p(to)
                logging.debug(
                    f'Cloning {private and "private" or "public"} {git_uri} to {to}')
                if private:
                    pat = os.environ.get('PRIVATE_ACCESS_TOKEN')
                    if pat is None:
                        die('Private repos without a PRIVATE_ACCESS_TOKEN - aborting.')
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

    def _process_module_docs(self, files: list, content: str, stack: str = '') -> None:
        stack_path = f'{stack}/{self.get("stack_path", "")}'
        path = f'{content}/docs/{stack_path}'
        if self.get('type') == 'module':
            foes = [f'{path}/{f}' for f in ['index.md', '_index.md']]
            l = len(foes)
            while l > 0:
                f = foes.pop(0)
                l -= 1
                if os.path.isfile(f):
                    foes.append(f)
            if len(foes) == 0:
                logging.warning(
                    f'no index.md nor _index.md found in {path} - please rectify the situation stat!!')
            if len(foes) > 1:
                logging.warning(
                    f'both index.md and _index.md exist in {path} - please address this immediately!!!')

            stack_weight = self.get('stack_weight')
            for f in foes:
                md = Markdown(f)
                md.fm_data['weight'] = stack_weight
                md.persist()

            files = run(f'find {path} -regex ".*\.md"').strip().split('\n')
            for f in files:
                md = Markdown(f)
                t = md.fm_data.pop('type', None)
                if t:
                    logging.warning(
                        f'the file {f} has a type set to `{t}` - please prevent future harm by acting now, thank you.')
                md.patch_module_paths(self)
                md.persist()

    def _get_docs(self, content: str, stack: str = '') -> list:
        docs = self._docs
        repo = self._git_clone(docs)
        branch = Component._get_dev_branch(docs)
        run(f'git checkout {branch}', cwd=repo)
        path = docs.get('path', '')
        stack_path = f'{stack}/{self.get("stack_path", "")}'
        if stack_path == '/':
            stack_path = ''
        logging.info(f'Copying docs')
        src = f'{repo}/{path}/'
        dst = f'{content}/docs/{stack_path}'
        mkdir_p(dst)
        files = rsync(src, dst)
        Component._dump_payload(src, dst, docs.get('payload', None))
        Component._add_meta_fm(docs.get('git_uri'), branch, dst, path)
        return files

    def _get_commands(self, content: str, commands: dict) -> list:
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

        for key in cmds:
            cmds[key]['module'] = self._type == 'module'
        commands.update(cmds)

        base = f'{repo}/{path}/'
        dst = f'{content}/commands/'
        srcs = [f'{base}{command_filename(cmd)}.md' for cmd in cmds]
        files = rsync(' '.join(srcs), dst)
        Component._dump_payload(base, dst,
                                self._commands.get('payload', None))
        Component._add_meta_fm(self._commands.get(
            'git_uri'), branch, dst, path)
        return files

    def _get_groups(self, groups: dict, versions: dict) -> None:
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
            if not groups.get(top):
                groups[top] = {}
                versions[top] = vdt
            if self._type == 'module':
                versions[top][key] = []
            groups[top][key] = d

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
            gh_token = os.environ.get('PRIVATE_ACCESS_TOKEN', None)
            for cat, subs in repos.items():
                for sub, rs in subs.items():
                    for n, d in rs.items():
                        logging.info(f'Getting stats for {n}')
                        r = Repository(d.get('repository'), gh_token)
                        r.update(repos[cat][sub][n])
                        repos[cat][sub][n] = r
                        pass
        dump_dict(f'data/repos.json', repos)

    def _get_misc(self, content) -> None:
        repo = self._git_clone(self._misc)
        branch = Component._get_dev_branch(self._misc)
        run(f'git checkout {branch}', cwd=repo)
        dst = f'{content}/{self._stack_path}'
        Component._dump_payload(repo, dst, self._misc.get('payload'))
        return

    def _persist_commands(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("commands")}'
        logging.info(f'Persisting commands: {filepath}')
        dump_dict(filepath, self._commands)

    def _persist_groups(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("groups")}'
        logging.info(f'Persisting groups: {filepath}')
        dump_dict(filepath, self._groups)

    def _persist_versions(self) -> None:
        filepath = f'{self._website.get("path")}/{self._website.get("versions")}'
        logging.info(f'Persisting versions: {filepath}')
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
        self._groups = {}
        self._commands = {}
        self._versions = {}
        self._website = self.get('website')
        self._stack_path = self.get('stack_path')

        content_path = f'{self._website.get("path")}/{self._website.get("content")}'
        rm_rf(content_path)
        mkdir_p(content_path)

        components = []
        for component in ['docs', 'modules', 'themes', 'assets']:
            components += self.get(component, [])
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
                    versions=self._versions, commands=self._commands)

        self._persist_commands()
        self._persist_groups()
        self._persist_versions()
        self._process_commands(content_path)
        self._process_docs(content_path)

    def _apply_core(self, content: str, groups: dict, versions: dict, commands: dict) -> list:
        files = self._get_docs(content)
        files += self._get_commands(content, commands)
        self._get_misc(content)
        self._get_groups(groups, versions)
        self._get_data()
        return files

    def _apply_docs(self, content: str) -> list:
        files = self._get_docs(content)
        self._get_misc(content)
        return files

    def _apply_module(self, content: str, stack: str, groups: dict, versions: dict, commands: dict) -> list:
        files = self._get_docs(content, stack)
        self._process_module_docs(files, content, stack)
        files += self._get_commands(content, commands)
        self._get_groups(groups, versions)
        return files

    def _apply_asset(self) -> list:
        if not self._repository:
            return
        repo = self._git_clone(self._repository)
        dev_branch = self._repository.get('dev_branch')
        run(f'git checkout {dev_branch}', cwd=repo)
        return Component._dump_payload(repo, './', self._repository.get('payload'))

    def apply(self, **kwargs) -> None:
        content = kwargs.pop('content', dict)
        stack = kwargs.pop('stack', dict)
        groups = kwargs.pop('groups', dict)
        versions = kwargs.pop('versions', dict)
        commands = kwargs.pop('commands', dict)
        logging.info(f'Applying {self._type}: {self._name}')
        if self._type == 'core':
            self._apply_core(content, groups, versions, commands, **kwargs)
        elif self._type == 'module':
            self._apply_module(content, stack, groups,
                               versions, commands, **kwargs)
        elif self._type == 'docs':
            self._apply_docs(content, **kwargs)
        elif self._type == 'asset':
            self._apply_asset(**kwargs)
        elif self._type == 'stack':
            self._apply_stack()
        else:
            die(f'Unknown component type: {self._type} - aborting.')
