import argparse
import json
import logging
import os
import re
from sre_constants import BRANCH
import subprocess
import sys

from typing import OrderedDict
from urllib.parse import urlparse

def command_filename(name):
    """ Return the base filename for a command """
    return name.lower().replace(' ', '-')


def log_func(args):
    caller = sys._getframe(1).f_code.co_name
    logging.debug('called %s(%s)', caller, args)


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


def load_dict(path: str) -> dict:
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
    return o


def dump_dict(path: str, map: dict) -> None:
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


def get_commands(commands_path: str, commands: dict) -> dict:
    ''' Merges commands.json and groups for a piece '''
    cmds = load_dict(commands_path)
    sinter = set(cmds).intersection(set(commands))
    if len(sinter) != 0:
        logging.error(f'Duplicate commands found - aborting.')
        logging.error(sinter)
        exit(1)

    return cmds

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
    tags = filter_by_res(tags, res.get('include_tag_regex'), res.get('exclude_tag_regexes'))
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
            payload.append((f'{docs_repo}/{docs_repo_path}/commands/{command_filename(cmd)}.md', website_commands))
        commands.update(cmds)
    if typo == 'core':
        payload.append((f'{docs_repo}/{docs_repo_path}/commands/_index.md', website_commands))
    elif typo == 'docs':
        payload.append((f'{docs_repo}/{docs_repo_path}/', website_content))
    payload += [(f'{docs_repo}/{p}', website_docs) for p in docs.get('copy', [])]

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

    for (s,d) in payload:
        do_or_die(['rsync', '-av', '--no-owner', '--no-group', s, d])

    return commands


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=str,
                        default='./data',
                        help='path to data')
    parser.add_argument('--skip-clone', action='store_true',
                        help='Python logging level (overwrites LOGLEVEL env var)')
    parser.add_argument('--loglevel', type=str,
                        default='INFO',
                        help='Python logging level (overwrites LOGLEVEL env var)')
    parser.add_argument('--tmp', type=str,
                        help='temporary path', default='/tmp')
    args = parser.parse_args()
    logging.basicConfig(level=os.environ.get(
        'LOGLEVEL', args.loglevel).upper())

    temp_dir = f'{args.tmp}/stack'
    do_or_die(['mkdir', '-p', temp_dir])

    stack = load_dict(f'{args.data}/stack.json')
    website = stack.get('website')
    website_path = website.get('path')
    website_content = f'{website_path}/{website.get("content")}'

    groups = OrderedDict(load_dict(f'{args.data}/groups.json'))
    commands = OrderedDict()
    for piece_file in stack['pieces']:
        piece = load_dict(f'{args.data}/components/{piece_file}')
        id = piece.get('id')
        typo = piece.get('type')
        logging.info(f'Processing {typo} {id}...')

        name = piece.get('name', id)
        piece_path = f'{temp_dir}/{id}'

        if typo =='core':
            commands = get_dev_docs(website, piece, piece_path, commands)
        elif typo == 'module':
            commands = get_dev_docs(website, piece, piece_path, commands)
            groups.update({
                piece.get('id'): {
                    'type': 'module',
                    'display': piece.get('name'),
                    'description': piece.get('description'),
                }
            })
        elif typo == 'docs':
            get_dev_docs(website, piece, piece_path, {})

    dump_dict(f'{website_content}/commands.json', commands)
    dump_dict(f'{args.data}/groups.json', groups)
