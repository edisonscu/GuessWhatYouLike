import pymongo

client = pymongo.MongoClient(
    'mongodb+srv://edison:87542100@cluster0-ngemq.mongodb.net/data?retryWrites=true&w=majority')

collection = client.data.restaurant_tag

collection.ensure_index([('location', '2dsphere')])

res = collection.aggregate([
    {
        "$geoNear": {
            "near": { 'type': "Point", 'coordinates': [ 121.57485815669959 ,25.08136182819049] },
            "distanceField":"distance",
            "maxDistance": 10000
        }
    },
    {
        "$project": {
            "distance":1,
            "location": 1,
            "title": 1,
            "rating": 1,
            "score": {
                "$reduce": {
                    "input": "$tags",
                    "initialValue": {
                        "like": 0,
                        "ok": 0,
                        "dislike": 0
                    },
                    "in": {
                        "$switch": {
                            "branches": [
                                {
                                    "case": {
                                        "$in": ["$$this.key", ["香腸", "海膽", "店家"]]
                                    },
                                    "then":{
                                        "like": {"$add": ["$$value.like", 1]},
                                        "ok": "$$value.ok",
                                        "dislike": "$$value.dislike"
                                    }
                                },
                                {
                                    "case": {
                                        "$in": ["$$this.key", ["飯", "份量"]]
                                    },
                                    "then":{
                                        "like": "$$value.like",
                                        "ok": {"$add": ["$$value.ok", 1]},
                                        "dislike": "$$value.dislike"
                                    }
                                },
                                {
                                    "case": {
                                        "$in": ["$$this.key", ["魚肉", "菜色"]]
                                    },
                                    "then":{
                                        "like": "$$value.like",
                                        "ok": "$$value.ok",
                                        "dislike": {"$add": ["$$value.dislike", 1]}
                                    }
                                }
                            ],
                            "default":{
                                "like": "$$value.like",
                                "ok": "$$value.ok",
                                "dislike": "$$value.dislike"
                            }
                        }
                    }
                }
            }
        }
    },
    {
        "$project": {
            "distance":1,
            "location": 1,
            "title": 1,
            "rating": 1,
            "score": {
                "$subtract": ["$score.like", "$score.dislike"]
            }
        }
    },
    {
        "$sort": {
            "score": -1
        }
    },
    {
        "$limit":10
    }
])

for i in res:
    print(i)
