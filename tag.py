import pymongo

client = pymongo.MongoClient("mongodb+srv://edison:87542100@cluster0-ngemq.mongodb.net/test?retryWrites=true&w=majority")#連ALTAS
db = client.data
collection = db.restaurant_tag

res = collection.aggregate([
    {'$unwind':{
        'path':'$tags'
    }},
    {'$group':{
        '_id':1,
        'tags':{
            '$addToSet':'$tags.key'
        }
    }}
])

print('start counting')

counter = {}
sum = 1

for r in res:
    print(len(r['tags']))
    for tag in r['tags']:
        print(sum)
        count = collection.aggregate([
            {'$match':{
                'tags':{'$elemMatch':{'key':tag}}
            }},
            {'$count':'title'}
        ])
        for t in count:
            counter[tag] = t['title']
        sum += 1
        if sum > 10:
            break

print(counter)

import json
with open('count.json', 'w',encoding='utf-8-sig') as outfile:
    json.dump(counter, outfile)