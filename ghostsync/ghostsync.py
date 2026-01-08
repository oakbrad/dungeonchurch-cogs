from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import error, question, success
import discord
import aiohttp
import asyncio
import logging
import jwt as pyjwt
import time
import re
from binascii import unhexlify
from discord.ui import Button, View

# Set up logging
log = logging.getLogger("red.ghostsync")
log.setLevel(logging.DEBUG)


class ConfirmLinkView(View):
    """Confirmation view for overwriting an existing link."""

    def __init__(self, cog, ctx, ghost_url: str, ghost_member: dict, new_member: discord.Member, existing_member: discord.Member):
        super().__init__(timeout=60)
        self.cog = cog
        self.ctx = ctx
        self.ghost_url = ghost_url
        self.ghost_member = ghost_member
        self.new_member = new_member
        self.existing_member = existing_member
        self.message = None

    @discord.ui.button(label="Yes, Overwrite", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command author can confirm.", ephemeral=True)
            return

        # Perform the link update
        current_note = self.ghost_member.get("note") or ""
        current_note = re.sub(r"\b\d{17,20}\b", "", current_note).strip()
        new_note = f"{self.new_member.id} {current_note}".strip() if current_note else str(self.new_member.id)

        if await self.cog._update_ghost_member_note(self.ghost_url, self.ghost_member["id"], new_note):
            link_view = GhostMemberLinkView(self.ghost_url, self.ghost_member["id"])
            await interaction.response.edit_message(
                content=success(f"`Linked {self.ghost_member.get('email')} to {self.new_member.display_name} (ID: {self.new_member.id})`"),
                view=link_view
            )
        else:
            await interaction.response.edit_message(
                content=error("`Failed to update Ghost member. Check API keys and permissions.`"),
                view=None
            )
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command author can cancel.", ephemeral=True)
            return

        await interaction.response.edit_message(content="`Link cancelled.`", view=None)
        self.stop()

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(content="`Link cancelled (timed out).`", view=None)
            except discord.HTTPException:
                pass


class GhostMemberLinkView(View):
    """View with a button linking to the Ghost member profile."""

    def __init__(self, ghost_url: str, member_id: str):
        super().__init__(timeout=None)
        profile_url = f"{ghost_url}/ghost/#/members/{member_id}"
        self.add_item(Button(label="View Member in Ghost", style=discord.ButtonStyle.link, url=profile_url))


class PaginatedListView(View):
    """Paginated view for displaying lists of items."""

    def __init__(self, ctx, items: list, title: str, per_page: int = 15):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.items = items
        self.title = title
        self.per_page = per_page
        self.page = 0
        self.max_page = (len(items) - 1) // per_page
        self.message = None

        # Remove buttons if only one page
        if self.max_page == 0:
            self.clear_items()
        else:
            self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= self.max_page

    def get_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        page_items = self.items[start:end]

        embed = discord.Embed(
            title=self.title,
            description="\n".join(page_items),
            color=0xff2600
        )
        embed.set_footer(text=f"Page {self.page + 1}/{self.max_page + 1} • {len(self.items)} total")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command author can navigate.", ephemeral=True)
            return
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the command author can navigate.", ephemeral=True)
            return
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass


class GhostSync(commands.Cog):
    """Sync Ghost blog subscriber status with Discord roles"""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=4206668008, force_registration=True
        )
        default_guild = {
            "ghost_url": None,           # Base URL of Ghost instance
            "sync_interval": 1800,       # Seconds between sync polls (30 minutes)
            "subscriber_role": None,     # Discord Role ID for subscribers
            "log_channel": None,         # Optional channel for notifications
            "sync_role": None,           # Secondary role to sync to subscriber role
        }
        self.config.register_guild(**default_guild)

        # Dict of tasks for each guild the bot is in
        self.guild_tasks = {}
        # Start tasks for existing guilds
        self.bot.loop.create_task(self.initialize_tasks())

    def cog_unload(self):
        """Cancel all background tasks when the cog is unloaded."""
        for task in self.guild_tasks.values():
            task.cancel()
        self.guild_tasks.clear()

    async def initialize_tasks(self):
        """Initialize background tasks for all guilds the bot is part of."""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.start_guild_task(guild)

    ### TASK MANAGEMENT METHODS

    async def start_guild_task(self, guild: discord.Guild):
        """Start the background task for a specific guild."""
        if guild.id in self.guild_tasks:
            log.info(f"Task already running for guild '{guild.name}'.")
            return
        task = asyncio.create_task(self.sync_guild_roles(guild))
        self.guild_tasks[guild.id] = task
        log.info(f"Started sync task for guild '{guild.name}'.")

    async def stop_guild_task(self, guild: discord.Guild):
        """Stop the background task for a specific guild."""
        task = self.guild_tasks.get(guild.id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.guild_tasks[guild.id]
            log.info(f"Stopped sync task for guild '{guild.name}'.")

    ### GHOST API HELPERS

    async def _generate_jwt(self) -> str | None:
        """Generate a JWT token for Ghost Admin API authentication."""
        tokens = await self.bot.get_shared_api_tokens("ghost")
        key_id = tokens.get("key_id")
        key_secret = tokens.get("key_secret")

        if not key_id or not key_secret:
            log.error("Ghost API keys not configured.")
            return None

        try:
            # Decode hex secret to bytes
            secret_bytes = unhexlify(key_secret)

            # Create JWT payload
            now = int(time.time())
            payload = {
                "aud": "/admin/",
                "iat": now,
                "exp": now + 300  # 5 minutes
            }

            # Sign token with key ID in header
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

    def _has_paid_access(self, ghost_member: dict) -> bool:
        """Check if a Ghost member has paid access (paid or comped)."""
        status = ghost_member.get("status", "")
        if status in ("paid", "comped"):
            return True
        # Fallback: check subscriptions array for backwards compatibility
        return len(ghost_member.get("subscriptions", [])) > 0

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
                url = f"{ghost_url}/ghost/api/admin/members/?limit={limit}&page={page}&include=subscriptions"
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
                        # Check pagination
                        meta = data.get("meta", {}).get("pagination", {})
                        if page >= meta.get("pages", 1):
                            break
                        page += 1
                except Exception as e:
                    log.error(f"Error fetching Ghost members: {e}")
                    return None

        return all_members

    async def _get_ghost_member_by_email(self, ghost_url: str, email: str) -> dict | None:
        """Fetch a single Ghost member by email."""
        token = await self._generate_jwt()
        if not token:
            return None

        headers = {"Authorization": f"Ghost {token}"}
        url = f"{ghost_url}/ghost/api/admin/members/?filter=email:{email}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        log.error(f"Ghost API error: HTTP {response.status}")
                        return None
                    data = await response.json()
                    members = data.get("members", [])
                    return members[0] if members else None
            except Exception as e:
                log.error(f"Error fetching Ghost member by email: {e}")
                return None

    async def _update_ghost_member_note(self, ghost_url: str, member_id: str, note: str) -> bool:
        """Update a Ghost member's note field."""
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
                "note": note
            }]
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.put(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        log.error(f"Ghost API error updating member: HTTP {response.status}")
                        return False
                    return True
            except Exception as e:
                log.error(f"Error updating Ghost member note: {e}")
                return False

    def _extract_discord_id(self, note: str | None) -> int | None:
        """Extract a Discord ID from a Ghost member's note field."""
        if not note:
            return None
        # Look for a 17-20 digit number (Discord snowflake ID)
        match = re.search(r"\b(\d{17,20})\b", note)
        if match:
            return int(match.group(1))
        return None

    ### MAIN SYNC LOOP

    async def sync_guild_roles(self, guild: discord.Guild):
        """Background task to sync Ghost subscriber status with Discord roles."""
        while True:
            try:
                # Retrieve guild-specific configurations
                ghost_url = await self.config.guild(guild).ghost_url()
                sync_interval = await self.config.guild(guild).sync_interval()
                subscriber_role_id = await self.config.guild(guild).subscriber_role()
                log_channel_id = await self.config.guild(guild).log_channel()
                sync_role_id = await self.config.guild(guild).sync_role()

                # Skip if not configured
                if not ghost_url or not subscriber_role_id:
                    log.debug(f"Guild '{guild.name}' not fully configured, skipping sync.")
                    await asyncio.sleep(sync_interval)
                    continue

                subscriber_role = guild.get_role(subscriber_role_id)
                if not subscriber_role:
                    log.warning(f"Subscriber role {subscriber_role_id} not found in guild '{guild.name}'.")
                    await asyncio.sleep(sync_interval)
                    continue

                # Get optional sync role
                sync_role = guild.get_role(sync_role_id) if sync_role_id else None

                # Fetch Ghost members
                members = await self._get_ghost_members(ghost_url)
                if members is None:
                    # API error - keep existing roles, optionally notify
                    if log_channel_id:
                        channel = guild.get_channel(log_channel_id)
                        if channel:
                            try:
                                await channel.send(error("`GhostSync: Failed to fetch Ghost members. Roles unchanged.`"))
                            except discord.Forbidden:
                                pass
                    await asyncio.sleep(sync_interval)
                    continue

                # Build set of Discord IDs with Ghost subscriptions
                ghost_subscriber_ids = set()
                for ghost_member in members:
                    discord_id = self._extract_discord_id(ghost_member.get("note"))
                    if not discord_id:
                        continue
                    if self._has_paid_access(ghost_member):
                        ghost_subscriber_ids.add(discord_id)

                # Process role sync
                roles_added = 0
                roles_removed = 0

                for discord_member in guild.members:
                    if discord_member.bot:
                        continue

                    has_role = subscriber_role in discord_member.roles

                    # Check if member should have subscriber role
                    has_ghost_subscription = discord_member.id in ghost_subscriber_ids
                    has_sync_role = sync_role and sync_role in discord_member.roles
                    should_have_role = has_ghost_subscription or has_sync_role

                    if should_have_role and not has_role:
                        try:
                            reason = "GhostSync: Active subscription" if has_ghost_subscription else f"GhostSync: Has {sync_role.name} role"
                            await discord_member.add_roles(subscriber_role, reason=reason)
                            roles_added += 1
                            log.debug(f"Added subscriber role to {discord_member} in {guild.name}")
                        except discord.Forbidden:
                            log.error(f"Missing permissions to add role to {discord_member}")
                    elif not should_have_role and has_role:
                        try:
                            await discord_member.remove_roles(subscriber_role, reason="GhostSync: No active subscription or sync role")
                            roles_removed += 1
                            log.debug(f"Removed subscriber role from {discord_member} in {guild.name}")
                        except discord.Forbidden:
                            log.error(f"Missing permissions to remove role from {discord_member}")

                log.info(f"Sync complete for '{guild.name}': +{roles_added} -{roles_removed} roles")

                # Wait for the next interval
                await asyncio.sleep(sync_interval)

            except asyncio.CancelledError:
                log.info(f"Sync task for guild '{guild.name}' has been cancelled.")
                break
            except Exception as e:
                log.error(f"Unexpected error in sync task for guild '{guild.name}': {e}")
                await asyncio.sleep(60)  # Wait before retrying after unexpected errors

    ### LISTENERS

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Start a sync task when the bot joins a new guild."""
        await self.start_guild_task(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Stop the sync task when the bot is removed from a guild."""
        await self.stop_guild_task(guild)

    ### COMMANDS

    @commands.group()
    @checks.is_owner()
    async def ghostsync(self, ctx: commands.Context):
        """Commands for managing Ghost subscriber role sync"""
        pass

    @ghostsync.command()
    async def settings(self, ctx: commands.Context) -> None:
        """Display the current GhostSync settings."""
        tokens = await self.bot.get_shared_api_tokens("ghost")
        has_keys = bool(tokens.get("key_id") and tokens.get("key_secret"))

        setting_list = {
            "Ghost URL": await self.config.guild(ctx.guild).ghost_url() or "Not Set",
            "Sync Interval (seconds)": await self.config.guild(ctx.guild).sync_interval(),
            "Subscriber Role": ctx.guild.get_role(await self.config.guild(ctx.guild).subscriber_role()) or "Not Set",
            "Role Sync (→ Subscriber)": ctx.guild.get_role(await self.config.guild(ctx.guild).sync_role()) or "Not Set",
            "Log Channel": ctx.guild.get_channel(await self.config.guild(ctx.guild).log_channel()) or "Not Set",
            "Ghost API Keys": "Set" if has_keys else "Not Set",
        }

        embed = discord.Embed(
            title="👻 GhostSync Settings",
            color=0xff2600
        )
        for setting, value in setting_list.items():
            embed.add_field(name=setting, value=f"```{value}```", inline=False)
        await ctx.send(embed=embed)

    @ghostsync.command()
    async def url(self, ctx: commands.Context, *, url: str = None) -> None:
        """Set the Ghost instance base URL."""
        if url is not None:
            # Strip trailing slash
            url = url.rstrip("/")
            await self.config.guild(ctx.guild).ghost_url.set(url)
            await ctx.send(success(f"`Ghost URL set to {url}`"))
        else:
            await ctx.send(question("`Please provide the Ghost instance URL (e.g., https://blog.example.com)`"))

    @ghostsync.command()
    async def interval(self, ctx: commands.Context, *, seconds: int = None) -> None:
        """Set the sync interval in seconds."""
        if seconds is not None and seconds >= 60:
            await self.config.guild(ctx.guild).sync_interval.set(seconds)
            await ctx.send(success(f"`Sync interval set to {seconds} seconds.`"))
        else:
            await ctx.send(question("`Please provide an interval of at least 60 seconds.`"))

    @ghostsync.command()
    async def role(self, ctx: commands.Context, role: discord.Role = None) -> None:
        """Set the Discord role to assign to subscribers."""
        if role is not None:
            await self.config.guild(ctx.guild).subscriber_role.set(role.id)
            await ctx.send(success(f"`Subscriber role set to {role.name}.`"))
        else:
            await ctx.send(question("`Please mention a role or provide a Role ID.`"))

    @ghostsync.command()
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
                await ctx.send(question("`Please mention a channel to set as log channel, or run without argument to clear.`"))

    @ghostsync.command()
    async def rolesync(self, ctx: commands.Context, role: discord.Role = None) -> None:
        """Set a secondary role to sync to the subscriber role (e.g., Server Boosters)."""
        if role:
            await self.config.guild(ctx.guild).sync_role.set(role.id)
            await ctx.send(success(f"`Role sync set: Members with {role.name} will also get the subscriber role.`"))
        else:
            current = await self.config.guild(ctx.guild).sync_role()
            if current:
                await self.config.guild(ctx.guild).sync_role.set(None)
                await ctx.send(success("`Role sync cleared.`"))
            else:
                await ctx.send(question("`Please mention a role to sync to subscriber role, or run without argument to clear.`"))

    @ghostsync.command()
    async def link(self, ctx: commands.Context, email: str, member: discord.Member) -> None:
        """Link a Ghost email to a Discord user (stores Discord ID in Ghost member notes)."""
        ghost_url = await self.config.guild(ctx.guild).ghost_url()
        if not ghost_url:
            await ctx.send(error("`Ghost URL not configured. Use [p]ghostsync url first.`"))
            return

        await ctx.defer()

        # Find Ghost member by email
        ghost_member = await self._get_ghost_member_by_email(ghost_url, email)
        if not ghost_member:
            await ctx.send(error(f"`No Ghost member found with email {email}`"))
            return

        # Check if already linked to someone in this server
        existing_discord_id = self._extract_discord_id(ghost_member.get("note"))
        if existing_discord_id:
            existing_member = ctx.guild.get_member(existing_discord_id)
            if existing_member:
                # Already linked to someone in this server - ask for confirmation
                view = ConfirmLinkView(self, ctx, ghost_url, ghost_member, member, existing_member)
                msg = await ctx.send(
                    f"`{email}` is already linked to {existing_member.mention}. Overwrite?",
                    view=view,
                    ephemeral=True
                )
                view.message = msg
                return

        # No existing link (or linked user not in server) - proceed directly
        current_note = ghost_member.get("note") or ""
        current_note = re.sub(r"\b\d{17,20}\b", "", current_note).strip()
        new_note = f"{member.id} {current_note}".strip() if current_note else str(member.id)

        if await self._update_ghost_member_note(ghost_url, ghost_member["id"], new_note):
            view = GhostMemberLinkView(ghost_url, ghost_member["id"])
            await ctx.send(success(f"`Linked {email} to {member.display_name} (ID: {member.id})`"), view=view)
        else:
            await ctx.send(error("`Failed to update Ghost member. Check API keys and permissions.`"))

    @ghostsync.command()
    async def unlink(self, ctx: commands.Context, target: str) -> None:
        """Remove Discord ID from a Ghost member's notes. Accepts email or @mention."""
        ghost_url = await self.config.guild(ctx.guild).ghost_url()
        if not ghost_url:
            await ctx.send(error("`Ghost URL not configured. Use [p]ghostsync url first.`"))
            return

        await ctx.defer()

        ghost_member = None

        # Check if target is a Discord mention or ID
        discord_id_match = re.match(r"<@!?(\d{17,20})>|(\d{17,20})", target)
        if discord_id_match:
            # It's a Discord mention or ID - search Ghost members for this ID
            discord_id = int(discord_id_match.group(1) or discord_id_match.group(2))
            members = await self._get_ghost_members(ghost_url)
            if members is None:
                await ctx.send(error("`Failed to fetch Ghost members. Check API keys.`"))
                return

            for member in members:
                member_discord_id = self._extract_discord_id(member.get("note"))
                if member_discord_id == discord_id:
                    ghost_member = member
                    break

            if not ghost_member:
                await ctx.send(error(f"`No Ghost member found linked to <@{discord_id}>`"))
                return
        else:
            # Assume it's an email
            ghost_member = await self._get_ghost_member_by_email(ghost_url, target)
            if not ghost_member:
                await ctx.send(error(f"`No Ghost member found with email {target}`"))
                return

        # Check if there's a Discord ID to remove
        current_note = ghost_member.get("note") or ""
        existing_discord_id = self._extract_discord_id(current_note)
        if not existing_discord_id:
            await ctx.send("`No Discord ID to unlink - nothing changed.`")
            return

        # Remove Discord ID from note
        new_note = re.sub(r"\b\d{17,20}\b", "", current_note).strip()

        if await self._update_ghost_member_note(ghost_url, ghost_member["id"], new_note):
            view = GhostMemberLinkView(ghost_url, ghost_member["id"])
            await ctx.send(success(f"`Unlinked Discord ID from {ghost_member.get('email')}`"), view=view)
        else:
            await ctx.send(error("`Failed to update Ghost member. Check API keys and permissions.`"))

    @ghostsync.command(name="list")
    async def list_linked(self, ctx: commands.Context) -> None:
        """List all Ghost members with Discord IDs in their notes."""
        ghost_url = await self.config.guild(ctx.guild).ghost_url()
        if not ghost_url:
            await ctx.send(error("`Ghost URL not configured. Use [p]ghostsync url first.`"))
            return

        await ctx.defer()

        members = await self._get_ghost_members(ghost_url)
        if members is None:
            await ctx.send(error("`Failed to fetch Ghost members. Check API keys.`"))
            return

        linked = []
        for ghost_member in members:
            discord_id = self._extract_discord_id(ghost_member.get("note"))
            if discord_id:
                discord_member = ctx.guild.get_member(discord_id)
                status = "Subscribed" if self._has_paid_access(ghost_member) else "Free"
                discord_name = discord_member.mention if discord_member else "⚠️ Not in Server"
                linked.append(f"**{ghost_member.get('email')}** -> {discord_name} ({status})")

        if not linked:
            await ctx.send("`No Ghost members have Discord IDs linked.`")
            return

        view = PaginatedListView(ctx, linked, "Linked Ghost Members")
        msg = await ctx.send(embed=view.get_embed(), view=view)
        view.message = msg

    @ghostsync.command()
    async def sync(self, ctx: commands.Context) -> None:
        """Force an immediate sync of subscriber roles."""
        ghost_url = await self.config.guild(ctx.guild).ghost_url()
        subscriber_role_id = await self.config.guild(ctx.guild).subscriber_role()
        sync_role_id = await self.config.guild(ctx.guild).sync_role()

        if not ghost_url or not subscriber_role_id:
            await ctx.send(error("`GhostSync not fully configured. Set URL and role first.`"))
            return

        subscriber_role = ctx.guild.get_role(subscriber_role_id)
        if not subscriber_role:
            await ctx.send(error("`Configured subscriber role not found.`"))
            return

        sync_role = ctx.guild.get_role(sync_role_id) if sync_role_id else None

        await ctx.defer()

        members = await self._get_ghost_members(ghost_url)
        if members is None:
            await ctx.send(error("`Failed to fetch Ghost members. Check API keys.`"))
            return

        # Build set of Discord IDs with Ghost subscriptions
        ghost_subscriber_ids = set()
        for ghost_member in members:
            discord_id = self._extract_discord_id(ghost_member.get("note"))
            if not discord_id:
                continue
            if self._has_paid_access(ghost_member):
                ghost_subscriber_ids.add(discord_id)

        roles_added = 0
        roles_removed = 0

        for discord_member in ctx.guild.members:
            if discord_member.bot:
                continue

            has_role = subscriber_role in discord_member.roles
            has_ghost_subscription = discord_member.id in ghost_subscriber_ids
            has_sync_role = sync_role and sync_role in discord_member.roles
            should_have_role = has_ghost_subscription or has_sync_role

            if should_have_role and not has_role:
                try:
                    await discord_member.add_roles(subscriber_role, reason="GhostSync: Manual sync")
                    roles_added += 1
                except discord.Forbidden:
                    pass
            elif not should_have_role and has_role:
                try:
                    await discord_member.remove_roles(subscriber_role, reason="GhostSync: Manual sync")
                    roles_removed += 1
                except discord.Forbidden:
                    pass

        await ctx.send(success(f"`Sync complete: +{roles_added} roles added, -{roles_removed} roles removed.`"))

    @ghostsync.command()
    async def orphans(self, ctx: commands.Context) -> None:
        """List Discord members who aren't linked to any Ghost account."""
        ghost_url = await self.config.guild(ctx.guild).ghost_url()

        if not ghost_url:
            await ctx.send(error("`Ghost URL not configured. Use [p]ghostsync url first.`"))
            return

        await ctx.defer()

        # Fetch all Ghost members and extract linked Discord IDs
        members = await self._get_ghost_members(ghost_url)
        if members is None:
            await ctx.send(error("`Failed to fetch Ghost members. Check API keys.`"))
            return

        linked_discord_ids = set()
        for ghost_member in members:
            discord_id = self._extract_discord_id(ghost_member.get("note"))
            if discord_id:
                linked_discord_ids.add(discord_id)

        # Find Discord members who aren't linked
        orphans = []
        for discord_member in ctx.guild.members:
            if discord_member.bot:
                continue
            if discord_member.id not in linked_discord_ids:
                orphans.append(f"{discord_member.mention}")

        if not orphans:
            await ctx.send("`No orphans found. All Discord members are linked in Ghost.`")
            return

        view = PaginatedListView(ctx, orphans, "Orphaned Discord Members")
        msg = await ctx.send(embed=view.get_embed(), view=view)
        view.message = msg

    @ghostsync.command()
    async def subscribers(self, ctx: commands.Context) -> None:
        """List all linked members who have an active subscription."""
        ghost_url = await self.config.guild(ctx.guild).ghost_url()
        if not ghost_url:
            await ctx.send(error("`Ghost URL not configured. Use [p]ghostsync url first.`"))
            return

        await ctx.defer()

        members = await self._get_ghost_members(ghost_url)
        if members is None:
            await ctx.send(error("`Failed to fetch Ghost members. Check API keys.`"))
            return

        # Get sync role if configured
        sync_role_id = await self.config.guild(ctx.guild).sync_role()
        sync_role = ctx.guild.get_role(sync_role_id) if sync_role_id else None

        # Build set of Ghost subscriber Discord IDs for exclusion from sync role list
        ghost_subscriber_ids = set()

        subscribers = []
        for ghost_member in members:
            discord_id = self._extract_discord_id(ghost_member.get("note"))
            if not discord_id:
                continue

            if not self._has_paid_access(ghost_member):
                continue

            ghost_subscriber_ids.add(discord_id)

            discord_member = ctx.guild.get_member(discord_id)
            discord_name = discord_member.mention if discord_member else "⚠️ Not in Server"

            # Get tier name from subscription (comped members will show "Comped")
            tier_name = "Unknown Tier"
            subscriptions = ghost_member.get("subscriptions", [])
            if subscriptions:
                sub = subscriptions[0]  # Get first/active subscription
                tier = sub.get("tier") or sub.get("price", {}).get("tier") or {}
                tier_name = tier.get("name", "Unknown Tier")
            elif ghost_member.get("status") == "comped":
                tier_name = "Comped"

            subscribers.append(f"**{ghost_member.get('email')}** -> {discord_name} ({tier_name})")

        # Build list of sync role members (include all, even Ghost subscribers)
        sync_role_members = []
        if sync_role:
            for discord_member in ctx.guild.members:
                if discord_member.bot:
                    continue
                if sync_role in discord_member.roles:
                    sync_role_members.append(discord_member.mention)

        if not subscribers and not sync_role_members:
            await ctx.send("`No subscribers found.`")
            return

        # Send Ghost subscribers embed
        if subscribers:
            view = PaginatedListView(ctx, subscribers, "Ghost Subscribers")
            msg = await ctx.send(embed=view.get_embed(), view=view)
            view.message = msg

        # Send sync role members embed (separate)
        if sync_role_members:
            sync_view = PaginatedListView(ctx, sync_role_members, f"{sync_role.name} (Synced)")
            sync_msg = await ctx.send(embed=sync_view.get_embed(), view=sync_view)
            sync_view.message = sync_msg
