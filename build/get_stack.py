import argparse
from dis import dis
from platform import release
import json
import yaml
import logging
from operator import mod
from pydoc import doc
import re
import subprocess
import sys


def do_or_die(args: list, cwd='./') -> bytes:
    sp = subprocess.Popen(
        args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = sp.communicate()
    if sp.returncode != 0:
        print(err.decode('utf-8'), file=sys.stderr)
        exit(sp.returncode)
    return out.decode('utf-8')


def merge_module_groups(dest: str, name: str, display: str, description: str) -> None:
    with open(dest, 'r') as file:
        d = json.load(file)
        d[name] = {
            'display': display,
            'description': description,
        }
        json.dump(d, open(dest, 'w'), indent=4)


def merge_module_commands(module: str, dest: str, src: str) -> None:
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
                        default='redis_stack_components.yml')
    parser.add_argument('--content_dir', type=str,
                        default='website/content/en')
    parser.add_argument('--commands_json', type=str,
                        default='website/data/commands.json')
    parser.add_argument('--groups_json', type=str,
                        default='website/data/groups.json')
    parser.add_argument('--tmp_dir', type=str,
                        help='temporary path', default='/tmp')
    args = parser.parse_args()

    with open(args.components, 'r') as file:
        stack = yaml.load(file, Loader=yaml.FullLoader)['components']
    for name, piece in stack.items():
        print(f"Processing {name} ...")
        type = piece['type']
        repo_path = f'{args.tmp_dir}/{name.lower()}'

        if 'git_url' in piece:
            git_url = piece['git_url']
            docs_git_url = piece.get('docs_git_url', git_url)
            do_or_die(['rm', '-rf', repo_path])
            do_or_die(['git', 'clone', docs_git_url, repo_path])
        elif 'git_path' in piece:
            repo_path = piece['git_path']
        else:
            print("Cannot determine git repo - aborting.", file=sys.stderr)
            exit(1)

        docs_branch = piece.get('docs_branch', 'master')
        docs_branch_postfix = piece.get('docs_branch_postfix', '')
        if docs_branch_postfix != "":
            docs_branch_postfix = f'-{docs_branch_postfix}'
        do_or_die(['git', 'checkout', f'origin/{docs_branch}{docs_branch_postfix}'], cwd=repo_path)

        if type == 'core':
            do_or_die(['rsync', '-av', '--no-owner', '--no-group', '--exclude=".*"',
                       f'{repo_path}/', args.content_dir])
        elif type == 'module':
            docs_path = piece.get('docs_path', '')
            piece_content_dir = f'{args.content_dir}/{name.lower()}'
            module = piece['module']
            do_or_die(['mkdir', '-p', piece_content_dir])
            do_or_die(['rsync', '-av', '--no-owner', '--no-group', 
                       f'{repo_path}/{docs_path}/docs/', piece_content_dir])
            do_or_die(['rsync', '-av', '--no-owner', '--no-group', 
                       f'{repo_path}/{docs_path}/commands/', f'{args.content_dir}/commands'])
            merge_module_commands(name.lower(), f'{args.content_dir}/commands/commands.json', f'{repo_path}/commands.json')

            # TODO: fix this in new JS filter
            # merge_module_groups(args.groups_json, module, name, piece.get('description', ''))
            merge_module_groups(args.groups_json, 'module', 'RedisStack', piece.get('description', 'TBD'))

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
