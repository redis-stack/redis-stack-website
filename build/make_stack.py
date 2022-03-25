import argparse
from component import Component
from datetime import datetime
import logging
import tempfile
from util import mkdir_p


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Builds a stack website')
    parser.add_argument('--stack', type=str,
                        default='./data/stack/index.json',
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
