import asyncio
import json
import logging
import sqlite3
import time

import discord
import requests
from discord import app_commands
from discord.ext import tasks

with open("config.json") as config_file:
    config = json.load(config_file)


def get_duel_role(wins):
    for win_threshold, role_name in config["role_wins"]:
        if wins >= win_threshold:
            return role_name
    return None


async def hypixel_request(url):
    conn = sqlite3.connect("members.db")
    cur = conn.cursor()
    cur.execute("SELECT response, time FROM cache WHERE url = ?", (url,))
    members = cur.fetchone()

    if members:
        if time.time() - members[1] < 3600:
            return json.loads(members[0])

        response = requests.get(url, headers={"API-Key": config["hypixel_api_key"]})
        cur.execute(
            "UPDATE cache SET response = ?, time = ? WHERE url = ?",
            (response.text, time.time(), url),
        )
        conn.commit()
        conn.close()

        await asyncio.sleep(2.5)

        return response.json()

    response = requests.get(url, headers={"API-Key": config["hypixel_api_key"]})
    cur.execute(
        "INSERT OR IGNORE INTO cache (url, response, time) VALUES (?, ?, ?)",
        (url, response.text, time.time()),
    )
    conn.commit()
    conn.close()

    await asyncio.sleep(2.5)

    return response.json()


class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.iteration = 0

    async def setup_hook(self):
        print(f"Logged in as {self.user}")
        update_members.start()


client = MyClient()
tree = app_commands.CommandTree(client)


async def manage_role(member, role_id, action):
    guild = client.get_guild(config["guild_id"])
    role = discord.utils.get(guild.roles, id=role_id)

    if not role:
        return ""

    if (action == "add" and role not in member.roles) or (
        action == "remove" and role in member.roles
    ):
        try:
            if action == "add":
                await member.add_roles(role)
            else:
                await member.remove_roles(role)
            return f"<@&{role_id}> "
        except discord.Forbidden:
            pass
    return ""


@tasks.loop(seconds=0.1)
async def update_members():
    conn = sqlite3.connect("members.db")
    cur = conn.cursor()
    cur.execute("SELECT discord, uuid, wins FROM members ORDER BY wins ASC")
    members = cur.fetchall()
    conn.close()

    if client.iteration >= len(members):
        client.iteration = 0

    guild = client.get_guild(930945255166075000)
    member_info = members[client.iteration]
    member_id, uuid, db_wins = member_info

    if uuid is None:
        client.iteration += 1
        return

    data = (await hypixel_request(f"https://api.hypixel.net/player?uuid={uuid}")).get(
        "player", {}
    )

    if data is None or data.get("displayname", "") == "":
        print(f"Player {uuid} not found, skipping")
        client.iteration += 1
        return

    wins = data.get("stats", {}).get("Duels", {}).get(config["hypixel_api_wins_key"], 0)

    if wins is None:
        print(f"Couldn't get wins from player {uuid}, skipping")
        client.iteration += 1
        return

    try:
        member = await guild.fetch_member(member_id)
    except discord.NotFound:
        print(f"Discord member ID {member_id} not found, removing from DB")

        conn = sqlite3.connect("members.db")
        cur = conn.cursor()
        cur.execute("DELETE FROM members WHERE discord = ?", (member_id,))
        conn.commit()
        conn.close()

        client.iteration += 1
        return
    except discord.DiscordException as e:
        print(f"Error fetching member {member_id}, skipping: {e}")

        client.iteration += 1
        return

    try:
        guild_data = (
            await hypixel_request(f"https://api.hypixel.net/guild?player={uuid}")
        ).get("guild", {})
        display_name = data.get("displayname", "")

        if guild_data and guild_data.get("tag"):
            new_nick = f"{display_name} [{guild_data.get('tag')}]"
        else:
            new_nick = display_name

        if member.display_name != new_nick:
            await member.edit(nick=new_nick)
    except discord.Forbidden:
        pass

    duel_role_name = get_duel_role(wins)
    if duel_role_name:
        await manage_role(member, config["role_ids"][duel_role_name], "add")
        await manage_role(member, config["role_ids"]["verified"], "add")

    for role_id in config["role_ids"].values():
        if (
            duel_role_name and role_id == config["role_ids"][duel_role_name]
        ) or role_id == config["role_ids"]["verified"]:
            continue
        await manage_role(member, role_id, "remove")

    if wins != db_wins:
        conn = sqlite3.connect("members.db")
        cur = conn.cursor()
        cur.execute("UPDATE members SET wins = ? WHERE discord = ?", (wins, member_id))
        conn.commit()
        conn.close()

    client.iteration += 1


@update_members.before_loop
async def before_update_members():
    await client.wait_until_ready()


@tree.command(
    name="verify",
    description="Verify to gain access to the server",
    guild=discord.Object(id=config["guild_id"]),
)
@app_commands.describe(name="Your hypixel username")
async def verify(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    try:
        uuid = requests.get(f"https://playerdb.co/api/player/minecraft/{name}").json()[
            "data"
        ]["player"]["raw_id"]
        data = (
            await hypixel_request(f"https://api.hypixel.net/player?uuid={uuid}")
        ).get("player", {})
    except KeyError:
        embed = discord.Embed(
            title="Verification Unsuccessful",
            description=f"{config['emojis']['cross']} **{name}** is an invalid IGN",
            color=config["colors"]["red"],
        )
        await interaction.edit_original_response(embed=embed)
        return

    ign = data.get("displayname", "")
    wins = data.get("stats", {}).get("Duels", {}).get(config["hypixel_api_wins_key"], 0)
    discord_tag = data.get("socialMedia", {}).get("links", {}).get("DISCORD", "")

    if not discord_tag:
        embed = discord.Embed(
            title="Verification Unsuccessful",
            description=f"{config['emojis']['cross']} **{ign}** does not have a discord linked on hypixel",
            color=config["colors"]["red"],
        )
        embed.set_image(url=config["error_gif"])

        await interaction.edit_original_response(embed=embed)
        return

    if discord_tag != interaction.user.name:
        embed = discord.Embed(
            title="Verification Unsuccessful",
            description=f"{config['emojis']['cross']} **{ign}'s** hypixel discord tag `{discord_tag}` does not match `{interaction.user.name}`",
            color=config["colors"]["red"],
        )
        embed.set_image(url=config["error_gif"])

        await interaction.edit_original_response(embed=embed)
        return

    try:
        guild_data = (
            await hypixel_request(f"https://api.hypixel.net/guild?player={uuid}")
        ).get("guild", {})
        guild_name = (
            f"is in **{guild_data.get('name', '')}** [{guild_data.get('tag', '')}]"
            if guild_data
            else "is not in a guild"
        )
    except TypeError:
        guild_data = {}
        guild_name = "is not in a guild"

    try:
        conn = sqlite3.connect("members.db")
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO members (discord, uuid) VALUES (?, ?)",
            (interaction.user.id, uuid),
        )
        cur.execute(
            "UPDATE members SET uuid = ? WHERE discord = ?", (uuid, interaction.user.id)
        )
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        embed = discord.Embed(
            title="Verification Unsuccessful",
            description=f"{config['emojis']['cross']} **{ign}** is already verified",
            color=config["colors"]["red"],
        )

        await interaction.edit_original_response(embed=embed)
        return

    added_roles = await manage_role(
        interaction.user, config["role_ids"].get(get_duel_role(wins)), "add"
    )
    added_roles += await manage_role(
        interaction.user, config["role_ids"]["verified"], "add"
    )
    removed_roles = ""
    for role_id in config["role_ids"].values():
        if role_id not in [
            config["role_ids"].get(get_duel_role(wins)),
            931948752598618183,
        ]:
            removed_roles += await manage_role(interaction.user, role_id, "remove")

    try:
        new_nick = (
            f"{ign} [{guild_data.get('tag', '')}]"
            if (guild_data and guild_data.get("tag"))
            else ign
        )
        await interaction.user.edit(nick=new_nick)
    except discord.Forbidden:
        pass

    embed = discord.Embed(
        title="Verification Successful",
        description=f"{config['emojis']['tick']} **{ign}** {guild_name}\n{config['emojis']['add']} **Added:** {added_roles or '`None`'}\n{config['emojis']['minus']} **Removed:** {removed_roles or '`None`'}",
        color=config["colors"]["green"],
    )
    embed.set_thumbnail(
        url=f"https://heads.discordsrv.com/head.png?uuid={uuid}&name={name}&overlay"
    )

    await interaction.edit_original_response(embed=embed)


client.run(config["discord_token"], log_level=logging.ERROR)
