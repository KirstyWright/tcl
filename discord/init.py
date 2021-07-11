from model import start, Ban, Server, session
from sqlalchemy import select
import discord
import configparser
import json
import admin

client = discord.Client()
config = configparser.ConfigParser()
config.read('config.ini')


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await refresh_servers(client)
    await admin.run_ban_list(client)


@client.event
async def on_guild_join(guild):
    print("Joined guild {}".format(guild.name))
    await refresh_servers(client)
    await admin.run_ban_list(client)


async def refresh_servers(client):
    servers = session.execute(select(Server)).scalars()
    for guild in client.guilds:
        exists = False
        for server in servers:
            if server.id == guild.id:
                exists = True
                break

        if not exists:
            channel = discord.utils.find(
                lambda m: m.name == 'tcl-bot', guild.channels)
            if channel:
                server = Server(id=guild.id, channel_id=channel.id)
                session.add(server)
                session.commit()
                await admin.send_welcome_message(client, server)
            else:
                print('No channel called tcl-bot in guild {}'.format(guild.name))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$tcl'):
        if message.author.id not in json.loads(config['DEFAULT']['DiscordAdmins']):
            await message.channel.send('You don\'t have power to do that.')
            return

        if message.channel.id != int(config['DEFAULT']['AdminChannelId']):
            await message.channel.send('This action can only be performed in the admin channel.')
            return

        if message.content.startswith('$tcl refresh'):
            await refresh_servers(client)
            await admin.run_ban_list(client)
            return

        await admin.run(message, client)


@client.event
async def on_raw_reaction_add(payload):
    channel = client.get_channel(payload.channel_id)
    if payload.member and payload.member.bot:
        return
    try:
        message = await channel.fetch_message(payload.message_id)
    except:
        return

    if message.author.id != client.user.id:
        return

    await admin.process_reaction(client, payload, message, channel)

client.admin_channel_id = config['DEFAULT']['AdminChannelId']
client.run(config['DEFAULT']['DiscordToken'])
