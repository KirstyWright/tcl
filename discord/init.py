from model import start, Ban, Server
from sqlalchemy import select
import discord
import configparser
import json

client = discord.Client()
session = start()[1]
config = configparser.ConfigParser()
config.read('config.ini')

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await run_ban_list()


async def run_ban_list():
    sql_result = session.execute(select(Ban).order_by(Ban.id))

    ban_list = {}
    for value in sql_result.scalars():
        ban_list[value.id] = value

    for guild in client.guilds:
        bans = await guild.bans()
        loop_ban_list = ban_list
        for ban in bans:
            if ban.user.id in loop_ban_list:
                del loop_ban_list[ban.user.id]
            elif ban.reason and ban.reason.startswith("TCL Bans:"):
                # Banned but not in ban list
                print("Unbanning {} from {}".format(ban.user.id, guild.name))

                # await guild.unban(ban.user)

        for id, ban in loop_ban_list.items():
            print("Banning {} from {}".format(id, guild.name))

            # await guild.ban(discord.Object(id), reason="TCL Bans: {}".format(ban.reason))


@client.event
async def on_guild_join(guild):
    print("Joined guild {}".format(guild.name))
    run_ban_list()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$tcl'):
        if message.author.id not in json.loads(config['DEFAULT']['DiscordAdmins']):
            await message.channel.send('You don\'t have power to do that')
            return
        list = message.content.split()
        if message.content.startswith('$tcl ban'):
            if len(list) < 4:
                await message.channel.send('Incorrect number of parameters.')
                return

            try:
                user = await client.fetch_user(int(list[2]))
                list.pop(0)
                list.pop(0)
                list.pop(0)

                ban_reason = " ".join(list)

                # Look in db
                results = session.execute(select(Ban).where(
                    Ban.id == user.id).order_by(Ban.id))

                if results.fetchone():
                    await message.channel.send('There is already a ban for this user.')
                    return

                embed = discord.Embed(
                    title="New ban", description="", color=0x00ff00)
                embed.add_field(
                    name="ID", value=user.id, inline=True)
                embed.add_field(
                    name="name", value=user.name, inline=True)
                embed.add_field(
                    name="display name", value=user.display_name, inline=True)
                embed.add_field(
                    name="Reason", value=ban_reason, inline=False)

                user = Ban(id=user.id, banned_by=message.author.id, reason=ban_reason)
                session.add(user)
                session.commit()

                await message.channel.send(embed=embed)
                await run_ban_list()

            except discord.NotFound:
                await message.channel.send('No user with that ID found.')
                return
            except ValueError:
                await message.channel.send('Not a valid user id')
                return
            except discord.HTTPException as e:
                print(e)
                await message.channel.send('An unknown error occurred.')
                return
        elif message.content.startswith('$tcl refresh'):
            await run_ban_list()
        elif message.content.startswith('$tcl list'):
            results = session.execute(select(Ban).order_by(Ban.id)).scalars()
            buffer = ""
            count = 0
            for result in results:
                user = await client.fetch_user(result.id)
                if user:
                    buffer = buffer + \
                        "🚫 ({} {}):   {} \n".format(
                            result.id, user.name, result.reason)
                    if count > 10:
                        await message.channel.send(buffer)
                        count = 0
                        count = count + 1
                        buffer = ""
            if buffer:
                await message.channel.send(buffer)
        elif message.content.startswith('$tcl unban'):
            if len(list) < 3:
                await message.channel.send('Incorrect number of parameters.')
                return

            try:
                user = await client.fetch_user(int(list[2]))

                result = session.execute(select(Ban).where(
                    Ban.id == user.id).order_by(Ban.id)).scalar()

                if not result:
                    await message.channel.send('There is no ban for this user.')
                    return

                session.delete(result)
                session.commit()
                await message.channel.send("Unbanned {} - {}".format(user.id, user.name))
                await run_ban_list()

            except discord.NotFound:
                await message.channel.send('No user with that ID found.')
                return
            except ValueError:
                await message.channel.send('Not a valid user id')
                return
            except discord.HTTPException as e:
                print(e)
                await message.channel.send('An unknown error occurred.')
                return
            await run_ban_list()

client.run(config['DEFAULT']['DiscordToken'])
