import argparse
import logging
import os
import sys
import urllib.error
from datetime import datetime
from stack.github import Repository
from stack.structured_data import load_dict, dump_dict
from stack.util import die, wget

def get_repositories(args: argparse.Namespace) -> None:
    production = args.production
    token = os.environ.get('PRIVATE_ACCESS_TOKEN')
    if not token and production:
        die('PRIVATE_ACCESS_TOKEN not provided for production mode - aborting.')

    try:
        meta_in = f'{args.input}{args.meta}'
        meta_out = f'{args.output}{args.meta}'
        wget(meta_in, meta_out)
        meta = load_dict(meta_out)
        logging.info(f'Merge metadata loaded from {meta_in}.')
    except urllib.error.URLError:
        meta = {}
        logging.warning(f'Merge metadata not found at {meta_in} - starting from scratch.')
    repos_in = f'{args.input}{args.repos}'
    repos_out = f'{args.output}{args.repos}'
    if os.path.exists(repos_out):
        logging.info(f'Repos data loaded locally from {repos_out}.')
    else:
        try:
            wget(repos_in, repos_out)
            logging.info(f'Repos metadata loaded from {repos_in}.')
        except urllib.error.URLError:
            die('Could not find repositories - aborting.')

    repos = load_dict(repos_out)
    for group in repos.values():
        for sub in group.values():
            for project in sub.values():
                repo = project.get('repository')
                if not meta.get(repo):
                    meta[repo] = {
                        'active': None,
                        'forks_count': None,
                        'license': None,
                        'pushed_at': None,
                        'open_issues_count': None,
                        'stargazers_count': None
                    }
    for repo, data in meta.items():
        fetched_at = meta[repo].get('fetched_at')
        now = datetime.now().timestamp()
        if not fetched_at or fetched_at + 3600 * args.expire < now:
            if production:
                logging.info(f'Getting meta for {repo}')
                data.update(Repository(repo, token))
                data.update({ 'fetched_at': datetime.now().timestamp() })
            else:
                logging.debug(f'Skipping meta for {repo} - not in production.')
        else:
            logging.info(f'Skipping meta for {repo} - last fetched {round((now - fetched_at) / 60)} minutes ago.')
    dump_dict(meta_out, meta)
    logging.info(f'Processed {len(meta)} repositories.')

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Gets repositories metadata')
    parser.add_argument('--repos', type=str,
                        default='repos.json',
                        help='repositories dict')
    parser.add_argument('--meta', type=str,
                        default='meta.json',
                        help='meta dict')
    parser.add_argument('--input', type=str,
                        default='https://redis-stack.io/',
                        help='path to input dicts')
    parser.add_argument('--output', type=str,
                        default='./data/',
                        help='path to output dicts')
    parser.add_argument('--expire', type=int,
                        default=24,
                        help='expire time in hours after last fetched_at')
    parser.add_argument('--production', action='store_true',
                        help='activates metadata fetching')
    parser.add_argument('--loglevel', type=str,
                        default='INFO',
                        help='Python logging level (overwrites LOGLEVEL env var)')
    return parser.parse_args()


if __name__ == '__main__':
    # Init
    ARGS = parse_args()

    # Do starry run
    logging.basicConfig(
        level=ARGS.loglevel, format=f'{sys.argv[0]}: %(levelname)s %(asctime)s %(message)s')
    print(f'GET REPOS')
    start = datetime.now()
    get_repositories(ARGS)
    total = datetime.now() - start
    print(f'+OK ({total.microseconds / 1000} ms)')
