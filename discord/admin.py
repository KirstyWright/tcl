from model import start, Ban, Server, BanServer, session
from sqlalchemy import select
import discord
import commands.admin


async def run_ban_list(client, single_guild_id=None):
    sql_result = session.execute(select(Ban).where(Ban.status == 1).order_by(Ban.id))

    ban_list = {}
    for value in sql_result.scalars():
        ban_list[value.id] = value

    for guild in client.guilds:

        if single_guild_id and guild.id != single_guild_id:
            continue

        server_row = session.execute(
            select(Server).where(Server.id == guild.id)).scalar()
        if not server_row or not server_row.channel_id:
            continue

        loop_ban_list = {}

        # Sync database bans
        for ban_row in ban_list.values():
            server_ban_row = False
            for temp in server_row.bans:
                if temp.ban_id == ban_row.id:
                    server_ban_row = temp
                    break
            if server_ban_row is False:
                print('cannot find ban, sending new one')
                server_ban_row = BanServer(
                    status="registered", ban_id=ban_row.id, server_id=server_row.id)
                session.add(server_ban_row)
                server_ban_row = session.execute(select(BanServer).where(
                    BanServer.ban_id == server_ban_row.ban_id).where(BanServer.server_id == server_row.id)).scalar()
                message = await send_ban_message(guild, server_ban_row, client)
                server_ban_row.message_id = message.id
                session.add(server_ban_row)
                session.commit()
            else:
                channel = client.get_channel(server_ban_row.server.channel_id)
                if not channel:
                    # channel = discord.utils.find(lambda m: m.name == 'tcl-bot', guild.channels)
                    continue  # TODO: catch here

                if (server_ban_row.message_id):
                    try:
                        message = channel.get_partial_message(server_ban_row.message_id)
                        #  TODO: only if ban content has changed
                        message = await send_ban_message(guild, server_ban_row, client, message)
                    except discord.errors.NotFound:
                        # Message does not exist, might have been deleted
                        message = await send_ban_message(guild, server_ban_row, client)

                    if message.id != server_ban_row.message_id:
                        print("Was previous ban message but unable to find.")
                        server_ban_row.message_id = message.id
                        session.add(server_ban_row)
                        session.commit()

            loop_ban_list[server_ban_row.ban_id] = server_ban_row

            # if (server_ban_row.status == 'approved'):
            #     await guild.ban(discord.Object(server_ban_row.ban_id), reason="TCL Bans: {}".format(server_ban_row.ban.reason))

        bans = await guild.bans()
        for ban in bans:
            if ban.user.id in loop_ban_list and loop_ban_list[ban.user.id].status == "approved":
                del loop_ban_list[ban.user.id]  # is bannable but already banned
            elif ban.reason and ban.reason.startswith("TCL Bans:"):
                # Banned but not in ban list
                print("Unbanning {} from {}".format(ban.user.id, guild.name))
                await admin_log(client, "Unbanning {} from {}".format(ban.user.id, channel.guild.name))
                await guild.unban(ban.user)

        for id, sban in loop_ban_list.items():
            if (sban.status == "approved"):
                await guild.ban(discord.Object(sban.ban_id), reason="TCL Bans: {}".format(sban.ban.reason))
                print("Banning {} from {}".format(id, guild.name))
                await admin_log(client, "Banning {} from {}".format(id, guild.name))


async def run(message, client):
    list = message.content.split()
    if message.content.startswith('$tcl new'):
        await commands.admin.start_draft_ban(client, message)
    elif message.content.startswith('$tcl refresh'):
        await run_ban_list(client)
    elif message.content.startswith('$tcl list'):
        results = session.execute(select(Ban).where(Ban.status == 1).order_by(Ban.id)).scalars()
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
            await run_ban_list(client)

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
    else:
        await commands.admin.continue_ban(client, message)
        await run_ban_list(client);


async def send_ban_message(guild, ban_server, client, message=None):
    reactions = []
    discord_user = await client.fetch_user(ban_server.ban_id)
    if not discord_user:
        return

    embed = discord.Embed(
        title="New addition to ban list", description="", color=0x384359)

    embed.add_field(name="Discord name", value="{} #{}".format(
        discord_user.name, discord_user.discriminator), inline=True)
    embed.add_field(name="Tarkov name", value=ban_server.ban.tarkov, inline=True)
    embed.add_field(name="Status", value="This individual **{}** currently banned in this discord server.".format((
        "is" if ban_server.status == 'approved' else "is not")), inline=False)
    embed.add_field(name="Ban reason",
                    value=ban_server.ban.reason if ban_server.ban.reason is not None else "None", inline=False)
    embed.add_field(
        name='Evidence', value=ban_server.ban.evidence if ban_server.ban.evidence is not None else "None", inline=False)
    if (ban_server.status == 'registered'):
        embed.add_field(
            name="Decision", value="If you wish to add this ban to your server then react to this message with a :thumbsup:.", inline=False)
        reactions.append('\U0001f44d')
    elif ban_server.status == 'approved':
        embed.add_field(
            name="Decision", value="You have approved this ban and this account is now banned from your discord server. You can unban this user by reacting to this message with a :thumbsdown:.", inline=False)
        reactions.append('\U0001f44e')
    else:
        embed.add_field(
            name="Decision", value="N/A", inline=False)

    channel = discord.utils.find(lambda m: m.name == 'tcl-bot', guild.channels)
    if (not channel):
        # TODO LOG HERE
        return

    if (message is None):
        message = await channel.send(embed=embed)
    else:
        await message.clear_reactions()
        await message.edit(embed=embed)

    for reaction in reactions:
        await message.add_reaction(reaction)

    return message


async def send_welcome_message(client, row):
    channel = client.get_channel(row.channel_id)
    if (channel):
        embed = discord.Embed(
            title="Welcome", description="""
            Welcome to TCL Bans, please make sure this BOT has permission to Manage Bans on this server. Messages will appear here when accounts are added to the TCL ban list.

            This channel should have no messages posted other than those by this account, do not delete any messages posted by this account.

            This account requires the following permissions in this channel:
            - View Channel
            - Manage Messages
            - Send Messages""", color=0x384359)
        message = await channel.send(embed=embed)
        await admin_log(client, "Bot added to {}, welcome message sent.".format(channel.guild.name))


async def process_reaction(client, payload, message, channel):
    row = session.execute(select(BanServer).where(
        BanServer.message_id == message.id)).scalar()
    if row:
        if payload.emoji.name == '\U0001f44d':
            # approve ban
            row.status = 'approved'
            session.add(row)
            session.commit()
        elif payload.emoji.name == '\U0001f44e':
            # remove ban
            row.status = 'registered'
            session.add(row)
            session.commit()

        await run_ban_list(client, channel.guild.id)

async def admin_log(client, message):
    channel = client.get_channel(int(client.admin_channel_id))
    if (channel):
        await channel.send('Information: {}'.format(message))
