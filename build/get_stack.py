import argparse
import json
import logging
import re
import subprocess
import sys

from os import environ
from urllib.parse import urlparse

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


def merge_module_groups(dest: str, name: str, display: str, description: str) -> None:
    log_func(locals())
    with open(dest, 'r') as file:
        d = json.load(file)
    d[name] = {
        'display': display,
        'description': description,
    }
    with open(dest, 'w') as file:
        json.dump(d, file, indent=4)


def merge_module_commands(module: str, dest: str, src: str) -> None:
    log_func(locals())
    # TODO: prevent command name collisions
    with open(src, 'r') as file:
        s = json.load(file)
    for c in s:
        s[c]['module'] = module
    with open(dest, 'r') as file:
        d = json.load(file)
    d.update(s)
    with open(dest, 'w') as file:
        json.dump(d, file, indent=4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--components', type=str,
                        default='redis_stack_components.json',
                        help='path to components file')
    parser.add_argument('--content', type=str,
                        help='path to website content',
                        default='website/content/en')
    parser.add_argument('--commands', type=str,
                        default='website/data/commands.json',
                        help='path to commands.json')
    parser.add_argument('--groups', type=str,
                        default='website/data/groups.json',
                        help='path to groups.json')
    parser.add_argument('--tmp', type=str,
                        help='temporary path', default='/tmp')
    args = parser.parse_args()

    LOGLEVEL = environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(level=LOGLEVEL)

    with open(args.components, 'r') as file:
        stack = json.load(file)
    for piece in stack:
        name = piece.pop('name')
        type = piece.pop('type')
        logging.info(f'Processing {name} ...')
        repo_path = f'{args.tmp}/{name.lower()}'

        git_url = urlparse(piece.pop('git_url'))
        docs_git_url = urlparse(piece.pop('docs_git_url'))
        docs_branch = piece.pop('docs_branch')
        docs_branch_postfix = piece.pop('docs_branch_postfix', '')

        if docs_git_url.scheme == 'https':
            repo_path = f'{args.tmp}/{name.lower()}'
            do_or_die(['rm', '-rf', repo_path])
            do_or_die(['git', 'clone', docs_git_url.geturl(), repo_path])
        elif docs_git_url.scheme == 'file':
            repo_path = docs_git_url.path
        else:
            logging.error("Cannot determine git repo - aborting.")
            exit(1)

        do_or_die(['git', 'checkout', f'origin/{docs_branch}{docs_branch_postfix}'], cwd=repo_path)

        if type == 'core':
            do_or_die(['rsync', '-av', '--no-owner', '--no-group', '--exclude=".*"',
                       f'{repo_path}/', args.content])
        elif type == 'module':
            docs_path = piece.get('docs_path', '')
            piece_content = f'{args.content}/{name.lower()}'
            module = piece.pop('module')
            do_or_die(['mkdir', '-p', piece_content])
            do_or_die(['rsync', '-av', '--no-owner', '--no-group', 
                       f'{repo_path}/{docs_path}/docs/', piece_content])
            do_or_die(['rsync', '-av', '--no-owner', '--no-group', 
                       f'{repo_path}/{docs_path}/commands/', f'{args.content}/commands'])
            merge_module_commands(name.lower(), f'{args.content}/commands/commands.json', f'{repo_path}/commands.json')

            # TODO: fix this in new JS filter
            # merge_module_groups(args.groups, module, name, piece.pop('description', ''))
            merge_module_groups(args.groups, 'module', 'RedisStack', piece.pop('description', 'TBD'))

            # Fetch release tags
            out = do_or_die(['git', 'tag'], cwd=repo_path)
            repo_tags = out.split('\n')
            release_tag_regex = re.compile(piece['release_tag_regex'])
            release_tags = [
                tag for tag in repo_tags if release_tag_regex.match(tag)]
            release_tags.sort(reverse=True)

            # for i in range(len(release_tags)):
            #     tag = release_tags[i]
            #     tag_dest = f'{piece_content_dir}/{tag}'
            #     do_or_die(['git', 'checkout', f'{release_tags[i]}{docs_branch_postfix}'], cwd=repo_path)
            #     do_or_die(['rsync', '-av', '--exclude=".*"', f'{repo_path}/{docs_path}/', tag_dest])

            #     if i == 0:
            #         do_or_die(['rsync', '-av', '--exclude=".*"', f'{repo_path}/{docs_path}/', piece_content_dir])
