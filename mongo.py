import pickle

from bson.binary import Binary, USER_DEFINED_SUBTYPE
from bson.codec_options import TypeDecoder, CodecOptions, TypeRegistry
from pymongo import MongoClient


def fallback_pickle_encoder(value):
    return Binary(pickle.dumps(value), USER_DEFINED_SUBTYPE)


class PickledBinaryDecoder(TypeDecoder):
    bson_type = Binary

    def transform_bson(self, value):
        if value.subtype == USER_DEFINED_SUBTYPE:
            return pickle.loads(value)
        return value


class MongoInstance:
    def __init__(self, mongodb_uri):
        codec_options = CodecOptions(
            type_registry=TypeRegistry([PickledBinaryDecoder()], fallback_encoder=fallback_pickle_encoder))

        self.client = MongoClient(mongodb_uri)
        self.db = self.client['trivicord']
        self.collection = self.db.get_collection('games', codec_options=codec_options)

    def get_game(self, game_id):
        result = self.collection.find_one({'game_id': game_id}, {'_id': 0, 'game_id': 0})
        return result['game']

    def save_game(self, game_id, game):
        ids = [c['game_id'] for c in self.collection.find({}, {'game_id': 1})]
        if game_id not in ids:
            self.collection.insert_one({'game_id': game_id, 'game': game})
        else:
            self.collection.update_one({'game_id': game_id}, {'$set': {'game': game}})

    def delete_game(self, game_id):
        self.collection.delete_many({'game_id': game_id})

    def get_games(self):
        return [(g['game_id'], g['game']) for g in self.collection.find({}, {'_id': 0})]


if __name__ == '__main__':
    from jeopardy import TriviaGame

    game = TriviaGame(1)

    mongo = MongoInstance('mongodb://localhost')

    mongo.save_game('1', game)

    print(mongo.get_games())

    for a in mongo.get_games():
        print(a)

    # mongo.delete_game_from_db('1')
