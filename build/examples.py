import json
from stack.example import Example

e = Example('Python', 'examples/json_search/main.py')
with open('content/en/examples.json','r') as f:
    j = json.load(f)
j['json_search']['Python']['highlight'] = e.hidden
with open('content/en/examples.json','w') as f:
    json.dump(j,f)
print(e.hidden)