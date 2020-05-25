import sqlite3

with sqlite3.connect('games.db') as conn:
    cur = conn.cursor()

    for c in range(5):
        cur.execute('insert into categories values (?, ?)', (c, 'Category ' + str(c)))

        for value in range(200, 1200, 200):
            insert = (value + c, 'Question category {}, value {}'.format(c, value),
                      'Answer category {}, value {}'.format(c, value), value, c)
            cur.execute('insert into questions values (?, ?, ?, ?, null, null, ?)', insert)
    conn.commit()
