import argparse
from datetime import datetime
import logging
import sys
import tempfile

from stack.component import Stack
from stack.util import mkdir_p


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Builds a stack website')
    parser.add_argument('--stack', type=str,
                        default='./data/stack/index.json',
                        help='path to stack definition')
    parser.add_argument('--skip-clone', action='store_true',
                        help='skips `git clone`')
    parser.add_argument('--loglevel', type=str,
                        default='INFO',
                        help='Python logging level (overwrites LOGLEVEL env var)')
    parser.add_argument('--tempdir', type=str,
                        help='temporary path', default=f'{tempfile.gettempdir()}')
    parser.add_argument('--module', type=str,
                        default='*',
                        help='builds a single module (implies core docs and assets)')
    return parser.parse_args()


if __name__ == '__main__':
    # Init
    ARGS = parse_args()
    mkdir_p(ARGS.tempdir)

    # Load settings
    STACK = Stack(ARGS.stack, None, ARGS.__dict__)

    # Make the stack
    logging.basicConfig(
        level=ARGS.loglevel, format=f'{sys.argv[0]}: %(levelname)s %(asctime)s %(message)s')
    print(f'APPLY STACK "{STACK._name}"')
    start = datetime.now()
    STACK.apply()
    total = datetime.now() - start
    print(f'+OK ({total.microseconds / 1000} ms)')
