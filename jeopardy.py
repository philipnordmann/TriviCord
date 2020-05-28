import csv
import html
import logging
import random

import requests
from tabulate import tabulate

import database

categories_url = {
    'JeopardyGame': 'https://jservice.io/api/categories?count={count}&offset={offset}',
    'TriviaGame': 'https://opentdb.com/api_category.php',
    'DatabaseGame': 'db',
    'CustomGame': 'csv'
}
category_url = {
    'JeopardyGame': 'https://jservice.io/api/category?id={id}',
    'TriviaGame': 'https://opentdb.com/api.php?amount={amount}&category={category_id}&difficulty={difficulty}',
    'DatabaseGame': 'db',
    'CustomGame': 'csv'
}

category_count = 5
supported_values = [200, 400, 600, 800, 1000]


class Game(object):
    def __init__(self, game_id):

        class_name = self.__class__.__name__
        self.categories_url = categories_url[class_name]
        self.category_url = category_url[class_name]
        self.id = game_id
        self.categories = list()
        self.get_new_categories()
        self.current_clue = None
        self.current_category = 0
        self.current_category_clue = (0, 0)
        self.answered_clue_values = list()
        self.board = list()

        for i in range(0, len(self.categories)):
            self.board.append(list())
            for _ in range(0, len(supported_values)):
                self.board[i].append(str(supported_values[i]))

    def get_new_categories(self):
        pass

    def get_new_question(self, category, value):
        self.current_category = self.categories[category]
        for i in range(0, len(self.current_category['clues'])):
            if value == self.current_category['clues'][i]['value']:
                self.current_category_clue = (category, i)
                self.current_clue = self.current_category['clues'][i]

        return self.current_clue['question']

    def get_answer(self):
        self.board[self.current_category_clue[1]][self.current_category_clue[0]] = '----'
        self.answered_clue_values.append((self.current_category_clue[0], self.current_clue['value']))
        return self.current_clue['answer']

    def get_board(self):
        titles = ["{}. {}".format(self.categories.index(c) + 1, c['title']) for c in self.categories]

        return tabulate(self.board, headers=titles, disable_numparse=True)


class JeopardyGame(Game):

    def get_new_categories(self):
        while len(self.categories) < category_count:
            r_cat = requests.get(
                self.categories_url.format(count=category_count - len(self.categories),
                                           offset=random.randint(1, 500)))
            logging.debug('made web request')

            if r_cat.status_code <= 399:
                data = r_cat.json()

                for category in data:
                    r = requests.get(self.category_url.format(id=category['id']))
                    if r.status_code <= 399:
                        full_category = r.json()

                        clue_list = list()

                        for clue in full_category['clues']:
                            if clue['value'] in supported_values \
                                    and clue['value'] not in [c['value'] for c in clue_list] \
                                    and not clue['invalid_count']:
                                clue_list.append(clue)

                        clue_list.sort(key=lambda c: c['value'])
                        full_category['clues'] = clue_list

                        if len(full_category['clues']) == len(supported_values):
                            self.categories.append(full_category)
                            logging.debug('added category', full_category['title'])
                        else:
                            logging.debug('skipped category', full_category['title'])
                    else:
                        raise ConnectionError()
            else:
                raise ConnectionError()


class TriviaGame(Game):
    category_config = {
        'easy': 2,
        'medium': 2,
        'hard': 1
    }

    def get_new_categories(self):

        r = requests.get(self.categories_url)
        if r.status_code <= 399:
            categories = r.json()['trivia_categories']
            categories = random.sample(categories, k=category_count)
            categories.sort(key=lambda e: e['id'])
            for category in categories:
                category['clues'] = list()
                logging.debug('adding category', category['name'])
                category['title'] = category['name']
                for diff in TriviaGame.category_config.keys():
                    cr = requests.get(self.category_url.format(category_id=category['id'],
                                                               amount=TriviaGame.category_config[diff],
                                                               difficulty=diff))
                    cr_data = cr.json()
                    for clue in cr_data['results']:
                        value = supported_values[len(category['clues'])]

                        answers = clue['incorrect_answers']
                        answers.append(clue['correct_answer'])

                        random.shuffle(answers)

                        question = clue['question'] + '\n'
                        question += 'Possible answers:\n'
                        question += '\n'.join(['  - {}'.format(a) for a in answers])

                        category['clues'].append(
                            {'question': html.unescape(question), 'answer': html.unescape(clue['correct_answer']),
                             'value': value})
                self.categories.append(category)


class DatabaseGame(Game):
    def get_new_categories(self):
        categories = random.sample(database.get_categories(), k=category_count)
        categories.sort(key=lambda e: e['id'])
        for category in categories:
            for value in supported_values:
                clue = random.choice(database.get_questions(category['id'], value))
                category['clues'].append(clue)
            self.categories.append(category)


class CustomGame(Game):

    def __init__(self, game_id, csv_attachment_url):
        self.csv_attachment_url = csv_attachment_url
        super().__init__(game_id)

    def get_new_categories(self):
        request_data = requests.get(self.csv_attachment_url)
        if request_data.status_code <= 399:

            csv_data = request_data.text.strip().split('\n')

            rows = csv.reader(csv_data, delimiter=';')

            csv_list = [r for r in rows]

            categories = [r[0] for r in csv_list]
            categories = random.sample(list(dict.fromkeys(categories)), k=category_count)
            categories = [{'title': c, 'clues': list()} for c in categories]
            categories.sort(key=lambda c: c['title'])

            for category in categories:
                for q in csv_list:
                    if q[0] == category['title']:
                        question = {'question': q[1], 'answer': q[2], 'value': int(q[3])}
                        category['clues'].append(question)
                self.categories.append(category)


if __name__ == '__main__':
    j = DatabaseGame(1)

    print(j.get_new_question(0, 600))
    print(j.get_answer())
    print(j.get_new_question(3, 400))
    print(j.get_answer())

    print(j.get_board())
