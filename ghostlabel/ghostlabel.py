from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import error, success
import discord
import aiohttp
import asyncio
import logging
import jwt as pyjwt
import time
import re
from binascii import unhexlify

log = logging.getLogger("red.ghostlabel")


class GhostLabel(commands.Cog):
    """Sync Discord roles to Ghost labels"""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=4206668009, force_registration=True
        )
        default_guild = {
            "ghost_url": None,
            "sync_interval": 1800,
            "mappings": {},  # {role_id_str: label_slug}
            "log_channel": None,
        }
        self.config.register_guild(**default_guild)

        self.guild_tasks = {}
        self.bot.loop.create_task(self.initialize_tasks())

    def cog_unload(self):
        for task in self.guild_tasks.values():
            task.cancel()
        self.guild_tasks.clear()

    async def initialize_tasks(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.start_guild_task(guild)

    ### TASK MANAGEMENT

    async def start_guild_task(self, guild: discord.Guild):
        if guild.id in self.guild_tasks:
            return
        task = asyncio.create_task(self.sync_guild_labels(guild))
        self.guild_tasks[guild.id] = task
        log.info(f"Started label sync task for guild '{guild.name}'.")

    async def stop_guild_task(self, guild: discord.Guild):
        task = self.guild_tasks.get(guild.id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.guild_tasks[guild.id]
            log.info(f"Stopped label sync task for guild '{guild.name}'.")

    ### GHOST API HELPERS

    async def _generate_jwt(self) -> str | None:
        tokens = await self.bot.get_shared_api_tokens("ghost")
        key_id = tokens.get("key_id")
        key_secret = tokens.get("key_secret")

        if not key_id or not key_secret:
            log.error("Ghost API keys not configured.")
            return None

        try:
            secret_bytes = unhexlify(key_secret)
            now = int(time.time())
            payload = {
                "aud": "/admin/",
                "iat": now,
                "exp": now + 300
            }
            token = pyjwt.encode(
                payload,
                secret_bytes,
                algorithm="HS256",
                headers={"kid": key_id}
            )
            return token
        except Exception as e:
            log.error(f"Failed to generate JWT: {e}")
            return None

    async def _get_ghost_labels(self, ghost_url: str) -> list | None:
        """Fetch all Ghost labels."""
        token = await self._generate_jwt()
        if not token:
            return None

        headers = {"Authorization": f"Ghost {token}"}
        url = f"{ghost_url}/ghost/api/admin/labels/"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        log.error(f"Ghost API error fetching labels: HTTP {response.status}")
                        return None
                    data = await response.json()
                    return data.get("labels", [])
            except Exception as e:
                log.error(f"Error fetching Ghost labels: {e}")
                return None

    async def _get_ghost_members(self, ghost_url: str) -> list | None:
        """Fetch all Ghost members with pagination."""
        token = await self._generate_jwt()
        if not token:
            return None

        headers = {"Authorization": f"Ghost {token}"}
        all_members = []
        page = 1
        limit = 100

        async with aiohttp.ClientSession() as session:
            while True:
                url = f"{ghost_url}/ghost/api/admin/members/?limit={limit}&page={page}&include=labels"
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            log.error(f"Ghost API error: HTTP {response.status}")
                            return None
                        data = await response.json()
                        members = data.get("members", [])
                        if not members:
                            break
                        all_members.extend(members)
                        meta = data.get("meta", {}).get("pagination", {})
                        if page >= meta.get("pages", 1):
                            break
                        page += 1
                except Exception as e:
                    log.error(f"Error fetching Ghost members: {e}")
                    return None

        return all_members

    async def _update_ghost_member_labels(self, ghost_url: str, member_id: str, labels: list) -> bool:
        """Update a Ghost member's labels."""
        token = await self._generate_jwt()
        if not token:
            return False

        headers = {
            "Authorization": f"Ghost {token}",
            "Content-Type": "application/json"
        }
        url = f"{ghost_url}/ghost/api/admin/members/{member_id}/"
        payload = {
            "members": [{
                "labels": labels
            }]
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.put(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        log.error(f"Ghost API error updating member labels: HTTP {response.status}")
                        return False
                    return True
            except Exception as e:
                log.error(f"Error updating Ghost member labels: {e}")
                return False

    def _extract_discord_id(self, note: str | None) -> int | None:
        """Extract a Discord ID from a Ghost member's note field."""
        if not note:
            return None
        match = re.search(r"\b(\d{17,20})\b", note)
        if match:
            return int(match.group(1))
        return None

    ### MAIN SYNC LOOP

    async def sync_guild_labels(self, guild: discord.Guild):
        """Background task to sync Discord roles to Ghost labels."""
        while True:
            try:
                ghost_url = await self.config.guild(guild).ghost_url()
                sync_interval = await self.config.guild(guild).sync_interval()
                mappings = await self.config.guild(guild).mappings()
                log_channel_id = await self.config.guild(guild).log_channel()

                if not ghost_url or not mappings:
                    log.debug(f"Guild '{guild.name}' not fully configured, skipping sync.")
                    await asyncio.sleep(sync_interval)
                    continue

                # Fetch all Ghost members
                ghost_members = await self._get_ghost_members(ghost_url)
                if ghost_members is None:
                    if log_channel_id:
                        channel = guild.get_channel(log_channel_id)
                        if channel:
                            try:
                                await channel.send(error("`GhostLabel: Failed to fetch Ghost members. Sync skipped.`"))
                            except discord.Forbidden:
                                pass
                    await asyncio.sleep(sync_interval)
                    continue

                # Build mapping of Discord ID -> Ghost member
                discord_to_ghost = {}
                for ghost_member in ghost_members:
                    discord_id = self._extract_discord_id(ghost_member.get("note"))
                    if discord_id:
                        discord_to_ghost[discord_id] = ghost_member

                labels_added = 0
                labels_removed = 0

                # Process each mapping
                for role_id_str, label_slug in mappings.items():
                    role_id = int(role_id_str)
                    role = guild.get_role(role_id)
                    if not role:
                        log.warning(f"Role {role_id} not found in guild '{guild.name}'.")
                        continue

                    # Get Discord members with this role
                    discord_members_with_role = {m.id for m in role.members if not m.bot}

                    # Process each Ghost member that has a linked Discord account
                    for discord_id, ghost_member in discord_to_ghost.items():
                        has_role = discord_id in discord_members_with_role
                        current_labels = ghost_member.get("labels", [])
                        current_label_slugs = {l.get("slug") for l in current_labels}
                        has_label = label_slug in current_label_slugs

                        if has_role and not has_label:
                            # Add label
                            new_labels = current_labels + [{"slug": label_slug}]
                            if await self._update_ghost_member_labels(ghost_url, ghost_member["id"], new_labels):
                                labels_added += 1
                                # Update local cache
                                ghost_member["labels"] = new_labels
                                log.debug(f"Added label '{label_slug}' to Ghost member {ghost_member.get('email')}")
                        elif not has_role and has_label:
                            # Remove label
                            new_labels = [l for l in current_labels if l.get("slug") != label_slug]
                            if await self._update_ghost_member_labels(ghost_url, ghost_member["id"], new_labels):
                                labels_removed += 1
                                ghost_member["labels"] = new_labels
                                log.debug(f"Removed label '{label_slug}' from Ghost member {ghost_member.get('email')}")

                log.info(f"Label sync complete for '{guild.name}': +{labels_added} -{labels_removed} labels")

                await asyncio.sleep(sync_interval)

            except asyncio.CancelledError:
                log.info(f"Label sync task for guild '{guild.name}' has been cancelled.")
                break
            except Exception as e:
                log.error(f"Unexpected error in label sync task for guild '{guild.name}': {e}")
                await asyncio.sleep(60)

    ### LISTENERS

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.start_guild_task(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        await self.stop_guild_task(guild)

    ### COMMANDS

    @commands.group()
    @checks.is_owner()
    async def ghostlabel(self, ctx: commands.Context):
        """Commands for syncing Discord roles to Ghost labels"""
        pass

    @ghostlabel.command()
    async def settings(self, ctx: commands.Context) -> None:
        """Display the current GhostLabel settings."""
        tokens = await self.bot.get_shared_api_tokens("ghost")
        has_keys = bool(tokens.get("key_id") and tokens.get("key_secret"))

        mappings = await self.config.guild(ctx.guild).mappings()
        mapping_count = len(mappings)

        setting_list = {
            "Ghost URL": await self.config.guild(ctx.guild).ghost_url() or "Not Set",
            "Sync Interval (seconds)": await self.config.guild(ctx.guild).sync_interval(),
            "Log Channel": ctx.guild.get_channel(await self.config.guild(ctx.guild).log_channel()) or "Not Set",
            "Ghost API Keys": "Set" if has_keys else "Not Set",
            "Mappings": f"{mapping_count} configured",
        }

        embed = discord.Embed(
            title="GhostLabel Settings",
            color=0xff2600
        )
        for setting, value in setting_list.items():
            embed.add_field(name=setting, value=f"```{value}```", inline=False)
        await ctx.send(embed=embed)

    @ghostlabel.command()
    async def url(self, ctx: commands.Context, *, url: str = None) -> None:
        """Set the Ghost instance base URL."""
        if url is not None:
            url = url.rstrip("/")
            await self.config.guild(ctx.guild).ghost_url.set(url)
            await ctx.send(success(f"`Ghost URL set to {url}`"))
        else:
            await ctx.send("`Please provide the Ghost instance URL (e.g., https://blog.example.com)`")

    @ghostlabel.command()
    async def interval(self, ctx: commands.Context, *, seconds: int = None) -> None:
        """Set the sync interval in seconds."""
        if seconds is not None and seconds >= 60:
            await self.config.guild(ctx.guild).sync_interval.set(seconds)
            await ctx.send(success(f"`Sync interval set to {seconds} seconds.`"))
        else:
            await ctx.send("`Please provide an interval of at least 60 seconds.`")

    @ghostlabel.command()
    async def logchannel(self, ctx: commands.Context, channel: discord.TextChannel = None) -> None:
        """Set or clear the log channel for sync notifications."""
        if channel:
            await self.config.guild(ctx.guild).log_channel.set(channel.id)
            await ctx.send(success(f"`Log channel set to {channel.mention}.`"))
        else:
            current = await self.config.guild(ctx.guild).log_channel()
            if current:
                await self.config.guild(ctx.guild).log_channel.set(None)
                await ctx.send(success("`Log channel cleared.`"))
            else:
                await ctx.send("`Please mention a channel to set as log channel, or run without argument to clear.`")

    @ghostlabel.command(name="set")
    async def set_mapping(self, ctx: commands.Context, role: discord.Role, label_slug: str) -> None:
        """Add or update a role-to-label mapping."""
        ghost_url = await self.config.guild(ctx.guild).ghost_url()
        if not ghost_url:
            await ctx.send(error("`Ghost URL not configured. Use [p]ghostlabel url first.`"))
            return

        await ctx.defer()

        # Validate that the label exists in Ghost
        labels = await self._get_ghost_labels(ghost_url)
        if labels is None:
            await ctx.send(error("`Failed to fetch Ghost labels. Check API keys.`"))
            return

        label_slugs = {l.get("slug") for l in labels}
        if label_slug not in label_slugs:
            available = ", ".join(sorted(label_slugs)) if label_slugs else "none"
            await ctx.send(error(f"`Label '{label_slug}' not found in Ghost. Available labels: {available}`"))
            return

        # Save the mapping
        async with self.config.guild(ctx.guild).mappings() as mappings:
            mappings[str(role.id)] = label_slug

        await ctx.send(success(f"`Mapping set: {role.name} -> {label_slug}`"))

    @ghostlabel.command()
    async def remove(self, ctx: commands.Context, role: discord.Role) -> None:
        """Remove a role-to-label mapping."""
        async with self.config.guild(ctx.guild).mappings() as mappings:
            if str(role.id) in mappings:
                del mappings[str(role.id)]
                await ctx.send(success(f"`Mapping removed for {role.name}.`"))
            else:
                await ctx.send(error(f"`No mapping found for {role.name}.`"))

    @ghostlabel.command(name="list")
    async def list_mappings(self, ctx: commands.Context) -> None:
        """List all configured role-to-label mappings."""
        mappings = await self.config.guild(ctx.guild).mappings()

        if not mappings:
            await ctx.send("`No mappings configured. Use [p]ghostlabel set <role> <label> to add one.`")
            return

        lines = []
        for role_id_str, label_slug in mappings.items():
            role = ctx.guild.get_role(int(role_id_str))
            role_name = role.name if role else f"Unknown ({role_id_str})"
            lines.append(f"**{role_name}** -> `{label_slug}`")

        embed = discord.Embed(
            title="GhostLabel Mappings",
            description="\n".join(lines),
            color=0xff2600
        )
        await ctx.send(embed=embed)

    @ghostlabel.command()
    async def sync(self, ctx: commands.Context) -> None:
        """Force an immediate sync of role-to-label mappings."""
        ghost_url = await self.config.guild(ctx.guild).ghost_url()
        mappings = await self.config.guild(ctx.guild).mappings()

        if not ghost_url:
            await ctx.send(error("`Ghost URL not configured. Use [p]ghostlabel url first.`"))
            return

        if not mappings:
            await ctx.send(error("`No mappings configured. Use [p]ghostlabel set <role> <label> first.`"))
            return

        await ctx.defer()

        # Fetch all Ghost members
        ghost_members = await self._get_ghost_members(ghost_url)
        if ghost_members is None:
            await ctx.send(error("`Failed to fetch Ghost members. Check API keys.`"))
            return

        # Build mapping of Discord ID -> Ghost member
        discord_to_ghost = {}
        for ghost_member in ghost_members:
            discord_id = self._extract_discord_id(ghost_member.get("note"))
            if discord_id:
                discord_to_ghost[discord_id] = ghost_member

        labels_added = 0
        labels_removed = 0

        for role_id_str, label_slug in mappings.items():
            role_id = int(role_id_str)
            role = ctx.guild.get_role(role_id)
            if not role:
                continue

            discord_members_with_role = {m.id for m in role.members if not m.bot}

            for discord_id, ghost_member in discord_to_ghost.items():
                has_role = discord_id in discord_members_with_role
                current_labels = ghost_member.get("labels", [])
                current_label_slugs = {l.get("slug") for l in current_labels}
                has_label = label_slug in current_label_slugs

                if has_role and not has_label:
                    new_labels = current_labels + [{"slug": label_slug}]
                    if await self._update_ghost_member_labels(ghost_url, ghost_member["id"], new_labels):
                        labels_added += 1
                        ghost_member["labels"] = new_labels
                elif not has_role and has_label:
                    new_labels = [l for l in current_labels if l.get("slug") != label_slug]
                    if await self._update_ghost_member_labels(ghost_url, ghost_member["id"], new_labels):
                        labels_removed += 1
                        ghost_member["labels"] = new_labels

        await ctx.send(success(f"`Sync complete: +{labels_added} labels added, -{labels_removed} labels removed.`"))
