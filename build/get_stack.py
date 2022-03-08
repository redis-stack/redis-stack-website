import argparse
from dis import dis
from platform import release
import json
import logging
from operator import mod
import re
import subprocess

def do_or_die(args: list, cwd='./') -> bytes:
    sp = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if sp.returncode != 0:
        exit(sp)
    return sp.stdout

def merge_module_groups(dest: str, name: str, display: str, description: str) -> None:
    d = json.load(open(dest, 'r'))
    d[name] = {
        'display': display,
        'description': description,
    }
    json.dump(d, open(dest, 'w'), indent=4)

def merge_module_commands(module:str, dest: str, src: str) -> None:
    # TODO: prevent command name collisions
    s = json.load(open(src, 'r'))
    for c in s:
        s[c]['module'] = module.lower()
    d = json.load(open(dest, 'r'))
    d.update(s)
    json.dump(d, open(dest, 'w'), indent=4)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stack_json',type=str,default='./redis_stack_components.json')
    parser.add_argument('--content_dir',type=str,default='./website/content/en')
    parser.add_argument('--commands_json',type=str,default='./website/data/commands.json')
    parser.add_argument('--groups_json',type=str,default='./website/data/groups.json')
    parser.add_argument('--tmp_dir',type=str,help='temporary path',default='/tmp')
    args = parser.parse_args()

    stack = json.load(open(args.stack_json,'r'))
    for piece in stack:
        name = piece.pop('name')
        type = piece.pop('type')
        git_url = piece.pop('git_url')
        docs_git_url = piece.pop('docs_git_url', git_url)
        repo_path = f'{args.tmp_dir}/{name.lower()}'
        docs_branch = piece.pop('docs_branch', 'master')


        # Clone the repo
        do_or_die(['rm', '-rf', repo_path])
        do_or_die(['git', 'clone', docs_git_url, repo_path])

        docs_branch_postfix = piece.pop('docs_branch_postfix', '')
        do_or_die(['git', 'checkout', f'origin/{docs_branch}{docs_branch_postfix}'], cwd=repo_path)

        if type == 'core':
            do_or_die(['rsync', '-av', '--exclude=".*"', f'{repo_path}/', args.content_dir])
        elif type == 'module':
            docs_path = piece.pop('docs_path', '')
            piece_content_dir = f'{args.content_dir}/{name.lower()}'
            do_or_die(['mkdir', '-p', piece_content_dir])
            do_or_die(['rsync', '-av', f'{repo_path}/{docs_path}/docs/', piece_content_dir])
            do_or_die(['rsync', '-av', f'{repo_path}/{docs_path}/commands/', f'{args.content_dir}/commands'])
            merge_module_commands(name.lower(), f'{args.content_dir}/commands/commands.json', f'{repo_path}/commands.json')

            merge_module_groups(args.groups_json, 'module', 'Stack', 'TBD')
            # TODO: delete the prev and uncomment the next
            # merge_module_groups(args.groups_json, name.lower(), name, piece.pop('description', ''))

            # Fetch release tags
            out = do_or_die(['git', 'tag'], cwd=repo_path)
            repo_tags = out.decode('utf-8').split('\n')
            release_tag_regex = re.compile(piece['release_tag_regex'])
            release_tags = [tag for tag in repo_tags if release_tag_regex.match(tag)]
            release_tags.sort(reverse=True)

            # for i in range(len(release_tags)):
            #     tag = release_tags[i]
            #     tag_dest = f'{piece_content_dir}/{tag}'
            #     do_or_die(['git', 'checkout', f'{release_tags[i]}{docs_branch_postfix}'], cwd=repo_path)
            #     do_or_die(['rsync', '-av', '--exclude=".*"', f'{repo_path}/{docs_path}/', tag_dest])

            #     if i == 0:
            #         do_or_die(['rsync', '-av', '--exclude=".*"', f'{repo_path}/{docs_path}/', piece_content_dir])

