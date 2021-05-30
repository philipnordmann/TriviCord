import logging
import os
import re
import sys
from argparse import ArgumentParser

from discord import DiscordException
from discord.ext import commands

from jeopardy import JeopardyGame, TriviaGame, DatabaseGame, CustomGame

answer_regex_filter = [
    (re.compile(r'!answer '), ''),
    (re.compile(r'</*[biu]>'), '')
]

players_str = 'Currently these people are registered:\n{players}'
no_game_running = "You don't have any games running. Maybe try starting one with !start"

point_emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']

bot = commands.Bot(command_prefix='!')
db = None


@bot.event
async def on_ready():
    logging.info(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_reaction_add(reaction, user):
    logging.debug('reaction added')
    if not user.bot:
        game_data = db.get_game(reaction.message.guild.id)
        if game_data:
            if reaction.emoji == '\U0001f3ae':
                if user.name not in [p['name'] for p in game_data['players']]:
                    game_data['players'].append({'name': user.name, 'points': 0})
                    db.save_game(reaction.message.guild.id, game_data)
                    message = 'Welcome to the game {player}!'.format(player=user.name)
                    logging.debug('player {} joined the game {}'.format(user.name, reaction.message.guild.id))

                    await reaction.message.channel.send(message)


@bot.event
async def on_reaction_remove(reaction, user):
    logging.debug('reaction removed')
    if not user.bot:
        game_data = db.get_game(reaction.message.guild.id)
        if game_data:
            if reaction.emoji == '\U0001f3ae':
                if user.name in [p['name'] for p in game_data['players']]:
                    for i, player in enumerate(game_data['players']):
                        if player['name'] == user.name:
                            game_data['players'].pop(i)
                    db.save_game(reaction.message.guild.id, game_data)
                    message = 'Ok {player}, you are not longer in the game.'.format(player=user.name)
                    logging.debug('player {} removed from the game {}'.format(user.name, reaction.message.guild.id))

                    await reaction.message.channel.send(message)


@bot.command(name='start', help='Starts a game of jeopardy')
async def start(ctx, data_source='trivia'):
    game_data = db.get_game(ctx.guild.id)
    if not game_data:

        await ctx.send('welcome to TriviCord, please give me a second to gather some questions...')
        await ctx.trigger_typing()
        game_data = dict()

        if data_source.lower() == 'jeopardy':
            game = JeopardyGame(ctx.guild.id)
        elif data_source.lower() == 'trivia':
            game = TriviaGame(ctx.guild.id)
        elif data_source.lower() == 'db':
            game = DatabaseGame(ctx.guild.id)
        elif data_source.lower() == 'custom':

            attachments = ctx.message.attachments

            if len(attachments) > 0:
                game = CustomGame(ctx.guild.id, attachments[0].url)
            else:
                await ctx.send('Please provide a csv file with the questions')
                return
        else:
            raise DiscordException()

        logging.info('starting new game in guild {} with data_source {}'.format(ctx.guild.id, data_source.lower()))

        game_data['game'] = game
        game_data['players'] = list()
        # game_data['players'].append({'name': ctx.author.name, 'points': 0})
        game_data['active_player'] = None
        game_data['objection_possible'] = False
        message = '```{board}```'.format(board=game_data['game'].get_board())
        message += players_str.format(players='\n'.join(['- ' + p['name'] for p in game_data['players']]))
        message += '\n\nto add more players, each player may send !enter or add the \U0001f3ae reaction'
        db.save_game(ctx.guild.id, game_data)
        send_message = await ctx.send(message)
        await send_message.add_reaction('\U0001f3ae')
    else:
        message = "There is already a game running. Type !end to end the game."
        await ctx.send(message)


@bot.command(name='enter', help='enter the game')
async def enter(ctx):
    game_data = db.get_game(ctx.guild.id)
    if game_data:
        if ctx.author.name not in [p['name'] for p in game_data['players']]:
            game_data['players'].append({'name': ctx.author.name, 'points': 0})
            message = 'Welcome to the game {player}!'.format(player=ctx.author.name)
            logging.debug('player {} joined the game {}'.format(ctx.author.name, ctx.guild.id))
        else:
            message = 'You are already registered, {player}.'.format(player=ctx.author.name)

        message += '\n' + players_str.format(
            players='\n'.join(['- ' + p['name'] for p in game_data['players']]))
        db.save_game(ctx.guild.id, game_data)
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='players', help='get the current board')
async def players(ctx):
    game_data = db.get_game(ctx.guild.id)
    if game_data:
        message = players_str.format(players='\n'.join(['- ' + p['name'] for p in game_data['players']]))
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='choose', help='choose category and value')
async def choose(ctx, category: int, value: int):
    category -= 1
    game_data = db.get_game(ctx.guild.id)
    if game_data:
        game = game_data['game']

        if (category, value) not in game.answered_clue_values:
            message = 'Here comes your question:\n' + game.get_new_question(category, value)
            game_data['active_player'] = ctx.author.name
        else:
            message = 'That question was already chosen, please select another one from the list\n```{board}```' \
                .format(board=game.get_board())
        db.save_game(ctx.guild.id, game_data)
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='answer', help='answer to your current question')
async def give_answer(ctx, player_answer: str):
    game_data = db.get_game(ctx.guild.id)
    if game_data:
        game = game_data['game']
        if game_data['active_player'] == ctx.author.name:
            answer = answer_filter(game.get_answer())
            player_answer = answer_filter(ctx.message.content)

            if answer.lower() == player_answer.lower():
                points = game.current_clue['value']
                total = 0
                for p in game_data['players']:
                    if p['name'] == ctx.author.name:
                        index = game_data['players'].index(p)
                        game_data['players'][index]['points'] += points
                        total = game_data['players'][index]['points']

                message = "That's correct! You earned {points} points.\nYou have {total} points in total!".format(
                    points=points, total=total)
                game_data['objection_possible'] = False
            else:
                message = 'Your not quite right. The correct answer would be:\n' + answer
                game_data['objection_possible'] = True

            game_data['active_player'] = None

            db.save_game(ctx.guild.id, game_data)

        elif game_data['active_player'] is not None:
            message = "Sorry, it's not your turn. {active_player} has to answer.".format(
                active_player=game_data['active_player'])
        else:
            message = 'Currently there is no open question.' + \
                      ' Please use !choose <Category Number> <Question Value> to get a new question!'

        message += '\n```{board}```'.format(board=game.get_board())

    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='board', help='get the current board')
async def board(ctx):
    game_data = db.get_game(ctx.guild.id)
    if game_data:
        game = game_data['game']
        message = 'Here is your board:\n```{board}```'.format(board=game.get_board())
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='points', help='get the current points of all players')
async def get_points(ctx):
    game_data = db.get_game(ctx.guild.id)
    if game_data:
        game = game_data['game']
        message = "Here are the points:\n"
        player_list = sorted(game_data['players'], key=lambda p: p['points'], reverse=True)
        message += '\n'.join(['- {}: {}'.format(p['name'], p['points']) for p in player_list])
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='end', help='end the game')
async def end(ctx):
    game_data = db.get_game(ctx.guild.id)
    if game_data:
        player_list = sorted(game_data['players'], key=lambda p: p['points'], reverse=True)
        message = f'Congratulations **{player_list[0]["name"]}**, you have won the match with a score of **{player_list[0]["points"]}**!\U0001f389\U0001f389\U0001f389'
        message += '\n\n'
        for i, player in enumerate(player_list[:9]):
            message += f"{point_emoji_list[i]} {player['name']} ({player['points']})\n"
        db.delete_game(ctx.guild.id)
        message += '\nEnding your game now'
    else:
        message = no_game_running

    await ctx.send(message)


@bot.command(name='objection', help='get points if you think you are right')
async def objection(ctx):
    game_data = db.get_game(ctx.guild.id)
    if game_data:
        if game_data['objection_possible']:
            game = game_data['game']
            points = game.current_clue['value']
            total = 0
            for p in game_data['players']:
                if p['name'] == ctx.author.name:
                    index = game_data['players'].index(p)
                    game_data['players'][index]['points'] += points
                    total = game_data['players'][index]['points']
            message = "Okay, I'm sorry!\nYou earned {points} points.\nYou have {total} points in total!".format(
                points=points, total=total)
            game_data['objection_possible'] = False
            db.save_game(ctx.guild.id, game_data)
        else:
            message = "Sorry, no objection possible now"
    else:
        message = no_game_running

    await ctx.send(message)


'''
@bot.command(name='test', help='tests some stuff')
async def test(ctx):
    embed_var = Embed(title="Title", description="Desc", color=0x00ff00)
    embed_var.add_field(name="Field1", value="hi", inline=False)
    embed_var.add_field(name="Field2", value="hi2", inline=True)

    message = await ctx.send(embed=embed_var)
    logging.debug(str(message))
    for emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣']:
        await message.add_reaction(emoji)

    def check(reaction_, user_):
        return not user_.bot and reaction_.emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣']

    reaction, user = await bot.wait_for('reaction_add', check=check)
    print(str(reaction.emoji), user)


def create_embed(title, description, field_values):
    embed = Embed(title=title, description=description, color=0x00ff00)

    for field, value in field_values:
        embed.add_field(name=field, value=value, inline=False)

    return embed
'''


def answer_filter(answer):
    for regex, sub in answer_regex_filter:
        answer = regex.sub(sub, answer)
    return answer


def main():
    parser = ArgumentParser()
    parser.add_argument('--token', '-t', type=str, dest='token')
    parser.add_argument('--database-type', '-d', type=str, dest='db_type')
    parser.add_argument('--database-uri', '-u', type=str, dest='db_uri')
    parser.add_argument('--verbose', '-v', action='count', default=0)

    args = parser.parse_args()

    if not args.db_type:
        db_type = os.getenv('DB_TYPE')
    else:
        db_type = args.db_type

    if not args.db_uri:
        db_uri = os.getenv('DB_URI')
    else:
        db_uri = args.db_uri

    if not args.token:
        token = os.getenv('DISCORD_TOKEN')
    else:
        token = args.token

    if args.verbose == 1:
        level = logging.INFO
    elif args.verbose >= 2:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logging.basicConfig(level=level)

    global db
    if db_type.lower() == 'mongodb':
        from mongo import MongoInstance
        db = MongoInstance(db_uri)
    elif db_type.lower() == 'sqlite':
        from sqlite import SQLiteInstance
        db = SQLiteInstance(db_uri)
    else:
        logging.error('Unknown database type {}'.format(db_type))
        sys.exit(1)

    bot.run(token)


if __name__ == '__main__':
    main()
