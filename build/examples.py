import json
from stack.example import Example

pe = Example('Python', 'examples/json_search/main.py')
je = Example('JavaScript', 'examples/json_search/index.js')
with open('data/examples.json','r') as f:
    j = json.load(f)
j['json_search']['Python']['hidden'] = pe.hidden
j['json_search']['Python']['highlight'] = pe.highlight
j['json_search']['JavaScript']['hidden'] = je.hidden
j['json_search']['JavaScript']['highlight'] = je.highlight
with open('data/examples.json','w') as f:
    json.dump(j,f, indent=2)
print(j)