import pymongo


def convertPrefToTags(pref):
    client = pymongo.MongoClient(
        'mongodb+srv://edison:87542100@cluster0-ngemq.mongodb.net/data?retryWrites=true&w=majority')

    collection = client.data.food_type_tags

    result = []

    for p in pref:
        res = collection.find_one({'foodType': p})
        result = result + res['tags']

    return result


def getRestuarantsByPref(pref, location):
    client = pymongo.MongoClient(
        'mongodb+srv://edison:87542100@cluster0-ngemq.mongodb.net/data?retryWrites=true&w=majority')

    collection = client.data.restaurant_tag

    collection.ensure_index([('location', '2dsphere')])

    like = convertPrefToTags(pref['like'])
    ok = convertPrefToTags(pref['ok'])
    dislike = convertPrefToTags(pref['dislike'])

    print(location)

    res = collection.aggregate([
        {
            "$geoNear": {
                "near": {'type': "Point", 'coordinates': location},
                "distanceField": "distance",
                "maxDistance": 10000
            }
        },
        {
            "$project": {
                "location": 1,
                "title": 1,
                "rating": 1,
                "score": {
                    "$reduce": {
                        "input": {
                            "$filter": {
                                "input": "$tags",
                                "as": "tag",
                                "cond": {
                                    "$or": [
                                        {
                                            "$gte": [
                                                "$$tag.count",
                                                {"$multiply": [
                                                    {"$size": "$tags"},
                                                    0.05
                                                ]}
                                            ]
                                        },
                                        {
                                            "$gte": ["$$tag.count", 20]
                                        }
                                    ]
                                }
                            }
                        },
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
                                            "$in": ["$$this.key", like]
                                        },
                                        "then":{
                                            "like": {"$add": [
                                                "$$value.like", {
                                                    "$size": {
                                                        "$filter": {
                                                            "input": like,
                                                            "as": "element",
                                                            "cond": {
                                                                "$eq": ["$$this.key", "$$element"]
                                                            }
                                                        }
                                                    }
                                                }
                                            ]},
                                            "ok": "$$value.ok",
                                            "dislike": "$$value.dislike"
                                        }
                                    },
                                    {
                                        "case": {
                                            "$in": ["$$this.key", ok]
                                        },
                                        "then":{
                                            "like": "$$value.like",
                                            "ok": {"$add": ["$$value.ok", {
                                                    "$size": {
                                                        "$filter": {
                                                            "input": ok,
                                                            "as": "element",
                                                            "cond": {
                                                                "$eq": ["$$this.key", "$$element"]
                                                            }
                                                        }
                                                    }
                                            }
                                            ]},
                                            "dislike": "$$value.dislike"
                                        }
                                    },
                                    {
                                        "case": {
                                            "$in": ["$$this.key", dislike]
                                        },
                                        "then":{
                                            "like": "$$value.like",
                                            "ok": "$$value.ok",
                                            "dislike": {"$add": ["$$value.dislike", {
                                                    "$size": {
                                                        "$filter": {
                                                            "input": dislike,
                                                            "as": "element",
                                                            "cond": {
                                                                "$eq": ["$$this.key", "$$element"]
                                                            }
                                                        }
                                                    }
                                            }]}
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
                "location": 1,
                "title": {
                    "$substrBytes": [
                        "$title",
                        0,
                        {"$subtract": [
                            {"$strLenBytes": "$title"},
                            16
                        ]}
                    ]
                },
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
            "$limit": 10
        }
    ])

    return res


if __name__ == '__main__':
    client = pymongo.MongoClient(
        "mongodb+srv://edison:87542100@cluster0-ngemq.mongodb.net/test?retryWrites=true&w=majority")  # 連ALTAS
    db = client.data
    collection = db.user
    condition = {'userId': "U56660ce1d3aca386f13aa1776bde96d5"}
    user = collection.find_one(condition)
    res = getRestuarantsByPref(
        user['preference'], [121.50962901408954, 25.038204111628566])

    for i in res:
        print(i)
