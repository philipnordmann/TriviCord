import pickle
import sqlite3


class SQLiteInstance:
    def __init__(self, database_name):
        self.db = database_name
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute('create table if not exists games (guild int primary key, game_data blob)')
            cur.execute('create table if not exists categories (id int primary key, name text)')
            cur.execute('create table if not exists questions (id int, question text,'
                        + ' answer text, value int, media blob, mediatype text, category_id int)')
            conn.commit()

    def save_game(self, guild_id, game):
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute('select guild from games')
            ids = [r[0] for r in cur.fetchall()]

        if guild_id not in ids:
            with sqlite3.connect(self.db) as conn:
                cur = conn.cursor()
                cur.execute('insert into games values (?, ?)', (guild_id, pickle.dumps(game)))
                conn.commit()
        else:
            with sqlite3.connect(self.db) as conn:
                cur = conn.cursor()
                cur.execute('update games set game_data = ? where guild = ?', (pickle.dumps(game), guild_id))
                conn.commit()

    def delete_game(self, guild_id):
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute('delete from games where guild = ?', (guild_id,))
            conn.commit()

    def get_game(self, guild_id):
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute('select game_data from games where guild = ?', (guild_id,))
            result = cur.fetchone()
        if result:
            return pickle.loads(result[0])
        else:
            return None

    def get_games(self):
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute('select guild, game_data from games')
            games = [(g[0], pickle.loads(g[1])) for g in cur.fetchall()]

        return games

    def get_categories(self):
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute('select id, name from categories')
            return [{'id': c[0], 'title': c[1], 'clues': list()} for c in cur.fetchall()]

    def get_questions(self, category_id, value):
        with sqlite3.connect(self.db) as conn:
            cur = conn.cursor()
            cur.execute('select question, answer, value from questions where category_id = ? and value = ?',
                        (category_id, value))
            return [{'question': q[0], 'answer': q[1], 'value': q[2]} for q in cur.fetchall()]
