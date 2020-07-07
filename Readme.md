# TriviCord
## About
TriviCord is a bot for [Discord](https://discord.com/) that gives you the possibility to play a trivia game like jeopardy.
<br/>
It uses the [jService](https://jservice.io/) and the [Open Trivia DB](https://opentdb.com/) apis to fetch questions in specific categories.

## How to use
You can add the bot [here](https://discord.com/api/oauth2/authorize?client_id=712643567889285171&permissions=129024&scope=bot).<br/>
Afterwards you can already start your game!
### Commands
Every command starts with ! and some have parameters.

```
!answer <Your answer>                        answer to your current question
!board                                       get the current board
!choose <category number> <question value>   choose category and value
!end                                         ends the game
!enter                                       enter the game
!objection                                   get points if you think you are right
!players                                     get the current board
!points                                      get the current points of all players
!start <api to use>                          Starts a game of TriviCord!
                                                <api to use> can be one of jeopardy, trivia or custom
                                                If you use custom you can upload your own questions by creating an 
                                                attachment in the format of:
                                                
                                                Category;Question;Answer;Value
                                                Category2;Question2;Answer2;Value
                                                
                                                where value can be one of 200, 400, 600, 800, 1000
```

## Do it on your own
The bot will save the states of games to a local sqlite database or a mongodb instance.
That also can contain questions that you can use as data source in start command.
