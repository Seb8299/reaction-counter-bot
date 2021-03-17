import discord
import json
from os.path import isfile
    
import sqlite3

from discord.ext import commands
client = commands.Bot(command_prefix="/", hello_command=None)

con = None

@client.event
async def on_ready():
    global con

    if (not isfile("bot.db")):
        con = sqlite3.connect('bot.db')

        cur = con.cursor()

        # Create table
        cur.execute('''CREATE TABLE reactions
                    (emoji text, name text, count integer, channel text)''')

        print("db created")
    else:
        con = sqlite3.connect('bot.db')

        # con.close()

@client.command(name="migrate")
async def reaction_counter(ctx):
    global con

    cur = con.cursor()

    cur.execute('SELECT channel FROM reactions WHERE channel = {0}'.format(str(ctx.channel.id)))

    if (cur.fetchone() != None):
        cur.execute('DELETE FROM reactions WHERE channel = {0}'.format(str(ctx.channel.id)))

    channel = client.get_channel(730839966472601622)
    messages = await ctx.channel.history(limit=10000).flatten()

    dataset = []
    
    for msg in messages:
        for reaction in msg.reactions:
            async for user in reaction.users():

                flag = False

                # durchsuche die liste ob reaction schonmal gesehen
                for i in range(len(dataset)):
                    if (reaction.emoji == dataset[i][0] and str(user.id) == dataset[i][1]):
                        dataset[i][2] += 1
                        flag = True
                        break

                if (not flag):
                    dataset.append([str(reaction.emoji), str(user.id), 1, str(ctx.channel.id)])

    cur.executemany('INSERT INTO reactions VALUES (?,?,?,?)', dataset)

    cur.execute('SELECT * FROM reactions')

    embed=discord.Embed(title="Migration complite ✅")
   
    await ctx.send(embed=embed)
    

@client.command(name="peek", aliases=["p"])
async def reaction_counter(ctx, arg1):
    global con

    cur = con.cursor()

    cur.execute('SELECT * FROM reactions WHERE emoji = "{0}" AND channel = "{1}" ORDER BY count DESC'.format(str(arg1), str(ctx.channel.id)))
    
    embed=discord.Embed(title="Mr. Corn found reactions", description="These Clients have reacted with {0}".format(arg1))

    for i in cur.fetchall():
        user = await client.fetch_user(int(i[1]))
        embed.add_field(name=user.name, value=i[2], inline=True)
        
    await ctx.send(embed=embed)


@client.event
async def on_raw_reaction_add(payload):
    global con

    cur = con.cursor()

    cur.execute('SELECT * FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))
    
    dataset = cur.fetchone()
    if (dataset != None):
        cur.execute('UPDATE reactions SET count = count + 1 WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))
    else:
        cur.execute('INSERT INTO reactions VALUES ("{0}", "{1}", {2}, "{3}")'.format(str(payload.emoji), str(payload.user_id), 1, str(payload.channel_id)))

    # con.close()

@client.event
async def on_raw_reaction_remove(payload):
    global con

    cur = con.cursor()

    cur.execute('SELECT count FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))
    
    count = cur.fetchone()
    if (count[0] > 0):
        cur.execute('UPDATE reactions SET count = count - 1 WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))
    else:
        cur.execute('DELETE FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))

    # con.close()

@client.event
async def on_reaction_clear(message, reactions):
    global con

    cur = con.cursor()

    for reaction in message.reactions:
        async for user in reaction.users():
            cur.execute('SELECT count FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))
            
            count = cur.fetchone()
            if (count[0] > 0):
                cur.execute('UPDATE reactions SET count = count - 1 WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))
            else:
                cur.execute('DELETE FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))


@client.event
async def on_message_delete(message):
    pass
    # global con

    # cur = con.cursor()

    # for reaction in message.reactions:
    #     async for user in reaction.users():
    #         cur.execute('SELECT count FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))
            
    #         count = cur.fetchone()
    #         if (count[0] > 0):
    #             cur.execute('UPDATE reactions SET count = count - 1 WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))
    #         else:
    #             cur.execute('DELETE FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))
    
    # print("done")

# handle discord token
config_file = open("config.json", "r").read()
config = json.loads(config_file)
token = config["token"]
client.run(token)
