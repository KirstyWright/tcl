import discord
from model import start, Ban, Server, BanServer, session
from sqlalchemy import select
# AdminChannelId


async def start_draft_ban(client, message):
    list = message.content.split()

    if len(list) < 3:
        await message.channel.send('Incorrect number of parameters.\nThe correct format is `$tcl new <user_id>` with `<user_id>` being replaced with the users discord id.')
        return

    result = session.execute(select(Ban).where(
        Ban.status >= 100).order_by(Ban.id)).scalar()

    if result:
        await message.channel.send('We are currently processing a ban for a user id of {}. Please finish or delete this ban before starting a new one.'.format(result.id))
        return

    try:
        discord_user = await client.fetch_user(int(list[2]))
    except discord.NotFound:
        await message.channel.send('No user with that ID found.')
    except ValueError:
        await message.channel.send('Not a valid user ID')
        return

    results = session.execute(select(Ban).where(
        Ban.id == discord_user.id).order_by(Ban.id))

    if results.fetchone():
        await message.channel.send('There is already a ban for this user.')
        return

    row = Ban(id=discord_user.id, status=100)
    session.add(row)
    session.commit()

    await message.channel.send("New ban started for `{} #{}`. What is this users Tarkov name? Remember to prefix your response with `$tcl`.".format(discord_user.name, discord_user.discriminator))


async def step_100(client, message, ban):
    content = await parse_content(message, 'tarkov')

    ban.tarkov = content
    ban.status = 101
    session.add(ban)
    session.commit()

    await message.channel.send("Tarkov name set to `{}`. What is the reason for this ban, you can be as descriptive as you like? Remember to prefix your response with `$tcl`.".format(content))


async def step_101(client, message, ban):
    content = await parse_content(message, 'reason')

    ban.reason = content
    ban.status = 102
    session.add(ban)
    session.commit()

    await message.channel.send("Reason set. Is there any evidence for this ban? Please add links, uploads are not recognised. Remember to prefix your response with `$tcl`.")


async def step_102(client, message, ban):
    content = await parse_content(message, 'evidence')

    ban.evidence = content
    ban.status = 103
    session.add(ban)
    session.commit()

    embed = await get_preview_embed(client, ban)

    await message.channel.send("Evidence set.")
    await message.channel.send(embed=embed)


async def step_103(client, message, ban):
    content = await parse_content(message, 'response')
    if (content.strip().lower() not in ['cancel', 'confirm']):
        await message.channel.send("You need to type `$tcl confirm` or `$tcl cancel`.")
        return

    if (content.lower() == "confirm"):
        ban.status = 1
        session.add(ban)
        await message.channel.send("Confirmed ban, server owners are being informed.")
    else:
        session.delete(ban)
        await message.channel.send("Cancelled ban. To start a new ban type `$tcl new <discordID>`.")
    session.commit()


async def parse_content(message, field_name):
    content = message.content[4:].strip()

    if not content:
        await message.channel.send("You need to enter a valid {}.".format(field_name))
        raise DiscordInputError()

    return content


async def continue_ban(client, message):
    result = session.execute(select(Ban).where(
        Ban.status >= 100).order_by(Ban.id)).scalar()

    if not result:
        return  # No ban in progress

    try:
        if result.status == 100:
            return await step_100(client, message, result)
        elif result.status == 101:
            return await step_101(client, message, result)
        elif result.status == 102:
            return await step_102(client, message, result)
        elif result.status == 103:
            return await step_103(client, message, result)

    except DiscordInputError:
        return


async def get_preview_embed(client, ban):
    discord_user = await client.fetch_user(ban.id)
    if not discord_user:
        return

    embed = discord.Embed(
        title="New addition to ban list", description="", color=0x384359)

    embed.add_field(name="Discord name", value="{} #{}".format(
        discord_user.name, discord_user.discriminator), inline=True)
    embed.add_field(name="Tarkov name", value=ban.tarkov, inline=True)
    embed.add_field(name="Status", value="This individual **{}** currently banned in this discord server.".format((
        "is not")), inline=False)
    embed.add_field(name="Ban reason",
                    value=ban.reason, inline=False)
    embed.add_field(
        name='Evidence', value=ban.evidence, inline=False)
    embed.add_field(
        name="Decision", value="If you wish to add this ban to your server then react to this message with a :thumbsup:.", inline=False)
    embed.add_field(
        name="Preview", value="This message is purely a preview of the ban message, you cannot ineract with it in any way. If the details in this ban are correct and you wish to confirm this ban please type `$tcl confirm`. Alternatively you can remove this ban by typing `$tcl cancel`.", inline=False)

    return embed


class DiscordInputError(Exception):
    """Error declared when an invalid input has been passed."""
    pass
