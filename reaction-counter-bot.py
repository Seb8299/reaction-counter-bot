import discord
import json
import os

from discord.ext import commands
client = commands.Bot(command_prefix="/", hello_command=None)

@client.command(name="peek", aliases=["p"])
async def reaction_counter(ctx, arg1):
        
    channel = client.get_channel(730839966472601622)
    messages = await ctx.channel.history().flatten()

    users = []
    counter = []
    
    for msg in messages:
        for reaction in msg.reactions:
            async for user in reaction.users():
                if (arg1 == reaction.emoji):
                    if (user in users):
                        counter[users.index(user)] += 1
                    else:
                        users.append(user)
                        counter.append(1)
    
    embed=discord.Embed(title="Mr. Corn found reactions", description="These Clients have reacted with {0}".format(arg1))

    for i in range(len(users)):
        embed.add_field(name=users[i].name, value=counter[i], inline=True)
        
    await ctx.send(embed=embed)

# handle discord token
config_file = open("config.json", "r").read()
config = json.loads(config_file)
token = config["token"]
client.run(token)