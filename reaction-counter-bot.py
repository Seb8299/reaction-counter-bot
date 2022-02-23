import discord
import sqlite3
import json
from os.path import isfile
from discord.ext import commands
import time
import sys
import threading
import asyncio

class DataSet:
    def __init__(self, emoji, user_id, channel_id):
        self.emoji = emoji
        self.user_id = user_id
        self.channel_id = channel_id
        self.n = 1

    def incr(self, n=1):
        self.n += n
    
    def equal(self, dataset):
        return (self.emoji == dataset.emoji 
            and self.user_id == dataset.user_id )
            # and self.channel_id == dataset.channel_id)

    def toList(self):
        return [self.emoji, self.user_id, self.n, self.channel_id]

client = commands.Bot(command_prefix="/", hello_command=None)

con = None
cur = None

LIMIT = 20
lock = asyncio.Lock()

global_dataset = []

@client.event
async def on_ready():
    global con
    global cur

    con = sqlite3.connect('bot.db')
    cur = con.cursor()

    time.sleep(1)

    # Create table
    cur.execute('''CREATE TABLE IF NOT EXISTS reactions
                (emoji text, name text, count integer, channel text)''')

    print("success")

def progress(count, total):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s \r' % (bar, percents, '%'))
    sys.stdout.flush() 

@client.command(name="migrate")
async def reaction_counter(ctx):
    print("start to migrate")
    global con
    global cur
    global global_dataset

    global_dataset = []

    cur.execute('SELECT channel FROM reactions WHERE channel = {0}'.format(str(ctx.channel.id)))

    if (cur.fetchone() != None):
        cur.execute('DELETE FROM reactions WHERE channel = {0}'.format(str(ctx.channel.id)))

    channel = client.get_channel(ctx.message.channel.id)
    messages = await ctx.channel.history(limit=None).flatten()

    print(f"Number of messages: {len(messages)}")


    tasks = []
    t = 0

    # create threads
    async for message in ctx.channel.history(limit=None).chunk(LIMIT):
        t += 1

        _task = asyncio.get_event_loop().create_task(migrate_chunk(message, ctx))
        tasks.append(_task)

        if len(message) < LIMIT:
            break

    print(f"start tasks: {t}")

    for i, task in enumerate(tasks):
        progress(i, t)
        await task

    progress(t, t)
    print()
        
    for g in global_dataset:
        cur.execute(f'INSERT INTO reactions VALUES ("{g.emoji}", "{g.user_id}", "{g.n}", "{g.channel_id}")')


    # cur.execute('SELECT * FROM reactions')

    embed=discord.Embed(title="Migration complete ✅")
    
    await ctx.send(embed=embed)

    con.commit()

async def migrate_chunk(messages, ctx):
    global global_dataset
    dataset = []
    
    for msg in messages:
        for reaction in msg.reactions:
            async for user in reaction.users():

                flag = False

                # durchsuche die liste ob reaction schonmal gesehen
                for i in range(len(dataset)):
                    if (reaction.emoji == dataset[i].emoji and str(user.id) == dataset[i].user_id):
                        dataset[i].incr()
                        flag = True
                        break

                if (not flag):
                    dataset.append(DataSet(str(reaction.emoji), str(user.id), str(ctx.channel.id)))


    await lock.acquire()
    try:
        if global_dataset == []:
            global_dataset = dataset
        else:
            for t in dataset:
                for s in global_dataset:
                    if (s.equal(t)):
                        s.incr(t.n)
                    else:
                        global_dataset.append(t)
    finally:
        lock.release()


@client.command(name="peek", aliases=["p"])
async def reaction_counter(ctx, arg1):
    global con
    global cur

    cur.execute('SELECT * FROM reactions WHERE emoji = "{0}" AND channel = "{1}" ORDER BY count DESC'.format(str(arg1), str(ctx.channel.id)))
    
    embed=discord.Embed(title="Mr. Corn found reactions", description="These Clients have reacted with {0}".format(arg1))

    for i in cur.fetchall():
        user = await client.fetch_user(int(i[1]))
        embed.add_field(name=user.name, value=i[2], inline=True)
    
    await ctx.send(embed=embed)

    con.commit()

@client.event
async def on_raw_reaction_add(payload):
    global con
    global cur

    cur.execute('SELECT * FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))
    dataset = cur.fetchone()

    if (dataset != None):
        cur.execute('UPDATE reactions SET count = count + 1 WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))
    else:
        cur.execute('INSERT INTO reactions VALUES ("{0}", "{1}", {2}, "{3}")'.format(str(payload.emoji), str(payload.user_id), 1, str(payload.channel_id)))

    con.commit()

@client.event
async def on_raw_reaction_remove(payload):
    global con
    global cur

    cur.execute('SELECT count FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))
    
    count = cur.fetchone()
    if (count[0] > 0):
        cur.execute('UPDATE reactions SET count = count - 1 WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))
    else:
        cur.execute('DELETE FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(payload.emoji), str(payload.user_id), str(payload.channel_id)))

    con.commit()

@client.event
async def on_reaction_clear(message, reactions):
    global con
    global cur

    for reaction in message.reactions:
        async for user in reaction.users():
            cur.execute('SELECT count FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))
            
            count = cur.fetchone()
            if (count[0] > 0):
                cur.execute('UPDATE reactions SET count = count - 1 WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))
            else:
                cur.execute('DELETE FROM reactions WHERE emoji = "{0}" AND name = "{1}" AND channel = "{2}"'.format(str(reaction.emoji), str(user.id), str(reaction.channel_id)))

    con.commit()

# @client.event
# async def on_message_delete(message):
#     pass
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
