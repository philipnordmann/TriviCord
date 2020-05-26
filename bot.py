import os
import re

from discord import DiscordException
from discord.ext import commands

import database
from jeopardy import JeopardyGame, TriviaGame, CustomGame

TOKEN = os.getenv('DISCORD_TOKEN')

answer_regex_filter = [
    (re.compile(r'!answer '), ''),
    (re.compile(r'</*[biu]>'), '')
]

players_str = 'Currently these people are registered:\n{players}'
no_game_running = "You don't have any games running. Maybe try starting one with !start"

games = dict()

bot = commands.Bot(command_prefix='!')


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='start', help='Starts a game of jeopardy')
async def start(ctx, data_source='trivia'):
    if ctx.guild.id not in games:
        await ctx.send('welcome to jeopardy discord edition, please give me a second to gather some clues...')
        games[ctx.guild.id] = dict()

        if data_source.lower() == 'jeopardy':
            game = JeopardyGame(ctx.guild.id)
        elif data_source.lower() == 'trivia':
            game = TriviaGame(ctx.guild.id)
        elif data_source.lower() == 'custom':
            game = CustomGame(ctx.guild.id)
        else:
            raise DiscordException()

        games[ctx.guild.id]['game'] = game
        games[ctx.guild.id]['players'] = list()
        games[ctx.guild.id]['players'].append({'name': ctx.author.name, 'points': 0})
        games[ctx.guild.id]['active_player'] = None
        games[ctx.guild.id]['objection_possible'] = False
        message = '```{board}```'.format(board=games[ctx.guild.id]['game'].get_board())
        message += players_str.format(players='\n'.join(['- ' + p['name'] for p in games[ctx.guild.id]['players']]))
        message += '\n\nto add more players, each player may send !enter'
        database.save_state_to_db(ctx.guild.id, games[ctx.guild.id])
    else:
        message = "There is already a game running. Type !end to end the game."

    await ctx.send(message)


@bot.command(name='enter', help='get the current board')
async def enter(ctx):
    if ctx.guild.id in games:
        if ctx.author.name not in [p['name'] for p in games[ctx.guild.id]['players']]:
            games[ctx.guild.id]['players'].append({'name': ctx.author.name, 'points': 0})
            message = 'Welcome to the game {player}!'.format(player=ctx.author.name)
        else:
            message = 'You are already registered, {player}.'.format(player=ctx.author.name)

        message += '\n' + players_str.format(
            players='\n'.join(['- ' + p['name'] for p in games[ctx.guild.id]['players']]))
        database.save_state_to_db(ctx.guild.id, games[ctx.guild.id])
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='players', help='get the current board')
async def players(ctx):
    if ctx.guild.id in games:
        message = players_str.format(players='\n'.join(['- ' + p['name'] for p in games[ctx.guild.id]['players']]))
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='choose', help='choose category and value')
async def choose(ctx, category: int, value: int):
    category -= 1
    if ctx.guild.id in games:
        game = games[ctx.guild.id]['game']

        print(game.answered_clue_values)
        if (category, value) not in game.answered_clue_values:
            message = 'Here comes your question:\n' + game.get_new_question(category, value)
            games[ctx.guild.id]['active_player'] = ctx.author.name
        else:
            message = 'That clue was already chosen, please select another one from the list\n```{board}```' \
                .format(board=game.get_board())
        database.save_state_to_db(ctx.guild.id, games[ctx.guild.id])
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='answer', help='answer to your current question')
async def give_answer(ctx, player_answer: str):
    if ctx.guild.id in games:
        game = games[ctx.guild.id]['game']
        if games[ctx.guild.id]['active_player'] == ctx.author.name:
            answer = answer_filter(game.get_answer())
            player_answer = answer_filter(ctx.message.content)

            if answer.lower() == player_answer.lower():
                points = game.current_clue['value']
                total = 0
                for p in games[ctx.guild.id]['players']:
                    if p['name'] == ctx.author.name:
                        index = games[ctx.guild.id]['players'].index(p)
                        games[ctx.guild.id]['players'][index]['points'] += points
                        total = games[ctx.guild.id]['players'][index]['points']

                message = "That's correct! You earned {points} points.\nYou have {total} points in total!".format(
                    points=points, total=total)
            else:
                message = 'Your not quite right. The correct answer would be:\n' + answer

            games[ctx.guild.id]['active_player'] = None
            games[ctx.guild.id]['objection_possible'] = True
            database.save_state_to_db(ctx.guild.id, games[ctx.guild.id])

        elif games[ctx.guild.id]['active_player'] is not None:
            message = "Sorry, it's not your turn. {active_player} has to answer.".format(
                active_player=games[ctx.guild.id]['active_player'])
        else:
            message = 'Currently there is no open question.' + \
                      ' Please use !choose <Category Number> <Question Value> to get a new question!'

        message += '\n```{board}```'.format(board=game.get_board())

    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='board', help='get the current board')
async def board(ctx):
    if ctx.guild.id in games:
        game = games[ctx.guild.id]['game']
        message = 'Here is your board:\n```{board}```'.format(board=game.get_board())
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='points', help='get the current points of all players')
async def get_points(ctx):
    if ctx.guild.id in games:
        game = games[ctx.guild.id]['game']
        message = "Here are the points:\n"
        player_list = sorted(games[ctx.guild.id]['players'], key=lambda p: p['points'], reverse=True)
        message += '\n'.join(['- {}: {}'.format(p['name'], p['points']) for p in player_list])
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='end', help='end the game')
async def end(ctx):
    if ctx.guild.id in games:
        message = 'Okay ending your game...'
        del games[ctx.guild.id]
        database.delete_game_from_db(ctx.guild.id)
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='objection', help='get points if you think you are right')
async def objection(ctx):
    if ctx.guild.id in games:
        if games[ctx.guild.id]['objection_possible']:
            game = games[ctx.guild.id]['game']
            points = game.current_clue['value']
            total = 0
            for p in games[ctx.guild.id]['players']:
                if p['name'] == ctx.author.name:
                    index = games[ctx.guild.id]['players'].index(p)
                    games[ctx.guild.id]['players'][index]['points'] += points
                    total = games[ctx.guild.id]['players'][index]['points']
            message = "Okay, I'm sorry!\nYou earned {points} points.\nYou have {total} points in total!".format(
                points=points, total=total)
            games[ctx.guild.id]['objection_possible'] = False
            database.save_state_to_db(ctx.guild.id, games[ctx.guild.id])
        else:
            message = "Sorry, no objection possible now"
    else:
        message = no_game_running

    await ctx.send(message)


def answer_filter(answer):
    for regex, sub in answer_regex_filter:
        answer = regex.sub(sub, answer)
    return answer


def init_games():
    for guild_id, game in database.get_all_states_from_db():
        print('got game with id ' + str(guild_id))
        games.update({guild_id: game})


if __name__ == '__main__':
    init_games()
    bot.run(TOKEN)
