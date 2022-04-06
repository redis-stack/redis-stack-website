from cmath import exp
from stack.syntax import Command
from stack.markdown import Markdown
import json

if __name__ == '__main__':
    with open('data/commands.json', 'r') as f:
        j = json.load(f)

    board = []
    for k in j:
        v = j.get(k)
        c = Command(k, v)
        sf = c.syntax()
        d = c.diagram()
        path = f'content/en/commands/{k.lower().replace(" ", "-")}/'
        md = Markdown(f'{path}index.md')
        md.fm_data.update({
            'syntax_str': str(c),
            'syntax_fmt': sf,
        })
        md.persist()
        with open(f'{path}syntax.svg', 'w+') as f:
            f.write(d)
    #     board.append(sf)
    # board.sort(key=lambda x: len(x))
    # for c in board:
    #     print(c)
