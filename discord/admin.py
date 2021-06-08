from model import start, Ban, Server, BanServer, session
from sqlalchemy import select
import discord


async def run_ban_list(client):
    sql_result = session.execute(select(Ban).order_by(Ban.id))

    ban_list = {}
    for value in sql_result.scalars():
        ban_list[value.id] = value

    for guild in client.guilds:

        server_row = session.execute(select(Server).where(Server.id == guild.id)).scalar()
        if not server_row or not server_row.channel_id:
            continue

        # Sync database bans
        for ban_row in ban_list.values():
            server_ban_row = False
            for temp in server_row.bans:
                if temp.ban_id == ban_row.id:
                    server_ban_row = temp
                    break
            if server_ban_row is False:
                print('cannot find ban, sending new one')
                server_ban_row = BanServer(status="registered", ban_id=ban_row.id, server_id=server_row.id)
                session.add(server_ban_row)
                server_ban_row = session.execute(select(BanServer).where(BanServer.ban_id == server_ban_row.ban_id).where(BanServer.server_id == server_row.id)).scalar()
                message = await send_ban_message(guild, server_ban_row, client)
                server_ban_row.message_id = message.id
                session.add(server_ban_row)
                session.commit()
            # For every ban we have that this server does not have a row for


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


async def run(message, client):
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

            row = Ban(id=user.id, banned_by=message.author.id,
                      reason=ban_reason)

            session.add(row)
            session.commit()

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
    elif message.content.startswith('$tcl refresh'):
        await run_ban_list(client)
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


async def send_ban_message(guild, ban_server, client, message=None):

    discord_user = await client.fetch_user(ban_server.ban_id)
    if not discord_user:
        return

    embed = discord.Embed(
        title="New addition to ban list", description="", color=0x384359)

    embed.add_field(name="Discord name", value="{} #{}".format(
        discord_user.name, discord_user.discriminator), inline=True)
    embed.add_field(name="Tarkov name", value="N/A", inline=True)
    embed.add_field(name="Status", value="This individual **{}** currently in this discord server.".format(
        "is" if guild.get_member(discord_user.id) is not None else "is not"), inline=False)
    embed.add_field(name="Ban reason",
                    value=ban_server.ban.reason if ban_server.ban.reason is not None else "None", inline=False)
    embed.add_field(
        name='Evidence', value=ban_server.ban.evidence if ban_server.ban.evidence is not None else "None", inline=False)
    if (ban_server.status == 'registered'):
        embed.add_field(
            name="Decision", value="If you wish to add this ban to your server then react to this message with a :thumbsup:.", inline=False)
    elif ban_server.status == 'approved':
        embed.add_field(
            name="Decision", value="You have approved this ban and this account is now banned from your discord server.", inline=False)
    else:
        embed.add_field(
            name="Decision", value="N/A", inline=False)

    channel = discord.utils.find(lambda m: m.name == 'tcl-bot', guild.channels)
    if (not channel):
        # TODO LOG HERE
        return

    if (not message):
        message = await channel.send(embed=embed)
        await message.add_reaction('\U0001f44d')
    else:
        await message.clear_reactions()
        message = await message.edit(embed=embed)
    # get channel in server

    return message


async def send_welcome_message(client, row):
    channel = client.get_channel(row.channel_id)
    if (channel):
        embed = discord.Embed(
            title="Welcome", description="Welcome to TCL Bans, please make sure this BOT has permission to Manage Bans on this server. Messages will appear here when accounts are added to the TCL ban list.", color=0x384359)
        message = await channel.send(embed=embed)


async def process_reaction(client, payload, message, channel):
    row = session.execute(select(BanServer).where(BanServer.message_id == message.id)).scalar()
    if row:
        if payload.emoji.name == '\U0001f44d':
            # approve ban
            row.status = 'approved'
            session.commit()
            await send_ban_message(channel.guild, row, client, message)
