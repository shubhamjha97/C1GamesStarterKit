import json

mapping = {}

begin_x, end_x = 13, 14
y = 0
curr_idx = 0

while(begin_x >= 0):
    for x in range(begin_x, end_x+1):
        mapping[curr_idx] = [x, y]
        curr_idx += 1
    begin_x -= 1
    end_x += 1
    y += 1

with open('coord_mapping.json', 'w+') as f:
    json.dump(mapping, f)
