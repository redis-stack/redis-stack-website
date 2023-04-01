import logging
import re

HIDE_START = 'HIDE_START'
HIDE_END = 'HIDE_END'
REMOVE_START = 'REMOVE_START'
REMOVE_END = 'REMOVE_END'
PREFIXES = {
    'python': '#',
    'javascript': '//',
}

class Example(object):
    language = None
    path = None
    content = None
    hidden = None
    highlight = None

    def __init__(self, language: str, path: str) -> None:
        if not PREFIXES.get(language.lower()):
            logging.error(f'Unknown language "{language}" for example {path}')
            return
        self.language = language.lower()
        self.path = path
        with open(path, 'r') as f:
            self.content = f.readlines()
        self.hidden = []
        self.highlight = []
        self.make_ranges()
        self.persist(self.path)

    def persist(self, path: str = None) -> None:
        if not path:
            path = self.path
        with open(path,'w') as f:
            f.writelines(self.content)

    def make_ranges(self) -> None:
        curr = 0
        highlight = 1
        hidden = None
        remove = None
        content = []
        hstart = re.compile(f'^{PREFIXES[self.language]}\\s?{HIDE_START}')
        hend = re.compile(f'^{PREFIXES[self.language]}\\s?{HIDE_END}')
        rstart = re.compile(f'^{PREFIXES[self.language]}\\s?{REMOVE_START}')
        rend = re.compile(f'^{PREFIXES[self.language]}\\s?{REMOVE_END}')
        while curr < len(self.content):
            l = self.content[curr]
            if re.search(hstart, l):
                if hidden is not None:
                    logging.error(f'Nested hidden anchor in {self.path}:L{curr+1} - aborting.')
                    return
                if highlight < curr:
                    self.highlight.append(f'{highlight}-{curr}')
                hidden = len(content)
            elif re.search(hend, l):
                if hidden is None:
                    logging.error(f'Closing hidden anchor w/o a start in {self.path}:L{curr+1} - aborting.')
                    return
                if len(content) - hidden == 1:
                    self.hidden.append(f'{hidden+1}')
                else:
                    self.hidden.append(f'{hidden+1}-{len(content)}')
                highlight = curr
                hidden = None
            elif re.search(rstart, l):
                if remove is not None:
                    logging.error(f'Nested remove anchor in {self.path}:L{curr+1} - aborting.')
                    return
            elif re.search(rend, l):
                if remove is None:
                    logging.error(f'Closing remove anchor w/o a start in {self.path}:L{curr+1} - aborting.')
                    return
                remove = None
            else:
                content.append(l)
            curr += 1
        if hidden is not None:
            logging.error(f'Unclosed hidden anchor in {self.path}:L{hidden+1} - aborting.')
            return
        if highlight < len(content):
            self.highlight.append(f'{highlight}-{len(content)}')

        self.content = content
