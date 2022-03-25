import argparse
import logging
import os
import urllib.error
from datetime import datetime
from stack.github import Repository
from stack.structured_data import load_dict, dump_dict
from stack.util import wget

def get_repositories(args: argparse.Namespace) -> None:
    production = args.production
    token = os.environ.get('PRIVATE_ACCESS_TOKEN')
    if not token:
        logging.info('PRIVATE_ACCESS_TOKEN not provided - skipping.')
        return
    try:
        wget(args.merge, args.output)
        meta = load_dict(args.output)
        logging.info(f'Merge metadata loaded from {args.merge}')
    except urllib.error.URLError as e:
        meta = {}
        logging.warning(f'Merge metadata not found at {args.merge} - starting from scratch.')
    input = load_dict(args.input)
    for group in input.values():
        for sub in group.values():
            for project in sub.values():
                repo = project.get('repository')
                if not meta.get(repo):
                    meta[repo] = {}
    for repo, data in meta.items():
        fetched_at = meta.get('fetched_at')
        now = datetime.now().timestamp()
        if not fetched_at or fetched_at + 3600 * args.expire < now:
            if production:
                logging.info(f'Getting meta for {repo}')
                data.update(Repository(repo, token))
                data.update({ 'fetched_at': datetime.now().timestamp() })
            else:
                logging.info(f'Skipping meta for {repo} - not in production.')
        else:
            logging.info(f'Skipping meta for {repo} - last fetch at {fetched_at}.')
    dump_dict(args.output, meta)
    logging.info(f'Processed {len(meta)} repositories.')

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Gets repositories metadata')
    parser.add_argument('--input', type=str,
                        default='./data/repos.json',
                        help='path to repos dict')
    parser.add_argument('--output', type=str,
                        default='./data/meta.json',
                        help='path to meta dict')
    parser.add_argument('--merge', type=str,
                        default='https://redis-stack/meta.json',
                        help='uri to merge meta dict')
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
        level=ARGS.loglevel, format='%(filename)s: %(levelname)s %(asctime)s %(message)s')
    print(f'GET REPOS')
    start = datetime.now()
    get_repositories(ARGS)
    total = datetime.now() - start
    print(f'+OK ({total.microseconds / 1000} ms)')
