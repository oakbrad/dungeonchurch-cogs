import re
import logging
import aiohttp
import discord
from discord.ui import Button, View
from redbot.core import commands, Config, checks
from redbot.core.utils.chat_formatting import error, success

log = logging.getLogger("red.lore")

# Constants
DEFAULT_PROMPT = (
    "You are the Oracle of Pyora, a librarian wizard who keeps the lore and secrets of "
    "this dark fantasy realm. Role play as the librarian handing over a tome and making "
    "a short comment or riddle alluding to its contents. One or two sentences. "
    "The document is titled: "
)

NO_RESULTS_PROMPT = (
    "You are the Oracle of Pyora, a librarian wizard. Role play as if you searched your "
    "library shelves but could not find the book the visitor asked for. One or two sentences, "
    "cryptic and slightly apologetic but mysterious. The visitor was looking for: "
)


class RefreshButton(Button):
    """Button to refresh the lore search."""

    def __init__(self, cog: "Lore", query: str, guild_id: int):
        super().__init__(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔮")
        self.cog = cog
        self.query = query
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            content, embeds, new_view = await self.cog._build_lore_response(
                self.guild_id, self.query
            )
            new_view.set_message(self.view.message)
            await self.view.message.edit(content=content, embeds=embeds, view=new_view)
        except Exception as e:
            log.error(f"Refresh failed: {e}")
            await interaction.followup.send(
                error("Failed to refresh lore."), ephemeral=True
            )


class LoreView(View):
    """View containing Refresh, Edit, and Collection buttons."""

    def __init__(
        self,
        cog: "Lore",
        query: str,
        guild_id: int,
        document_url: str | None = None,
        collection_name: str | None = None,
        collection_url: str | None = None,
        timeout: float = 300,
    ):
        super().__init__(timeout=timeout)
        self.message = None

        # Refresh button
        self.add_item(RefreshButton(cog, query, guild_id))

        # Edit button (link to document)
        if document_url:
            self.add_item(
                Button(
                    label="Edit",
                    style=discord.ButtonStyle.link,
                    url=document_url,
                    emoji="📝",
                )
            )

        # Collection button (link to collection page)
        if collection_url and collection_name:
            self.add_item(
                Button(
                    label=collection_name,
                    style=discord.ButtonStyle.link,
                    url=collection_url,
                    emoji="📚",
                )
            )

    def set_message(self, message: discord.Message):
        self.message = message

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.NotFound:
                pass


class Lore(commands.Cog):
    """Query the Outline wiki for lore."""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=4206661337, force_registration=True)
        default_guild = {
            "wiki_url": None,
            "prompt": None,
            "no_results_prompt": None,
        }
        self.config.register_guild(**default_guild)

    # --- API Helper Methods ---

    async def _outline_request(
        self, guild_id: int, endpoint: str, payload: dict
    ) -> dict | None:
        """Make a POST request to Outline API."""
        api_key = (await self.bot.get_shared_api_tokens("outline")).get("api_key")
        if not api_key:
            return None

        base_url = await self.config.guild_from_id(guild_id).wiki_url()
        url = f"{base_url}/api/{endpoint}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        log.error(f"Outline API error {resp.status}: {await resp.text()}")
                        return None
                    return await resp.json()
        except aiohttp.ClientError as e:
            log.error(f"Outline request failed: {e}")
            return None
        except Exception as e:
            log.error(f"Outline request error: {e}")
            return None

    async def _search_documents(self, guild_id: int, query: str, limit: int = 5) -> list | None:
        """Search Outline wiki documents."""
        data = await self._outline_request(
            guild_id, "documents.search", {"query": query, "limit": limit}
        )
        if data:
            return data.get("data", [])
        return None

    async def _get_backlinks(self, guild_id: int, document_id: str, limit: int = 5) -> list:
        """Fetch documents that link to the given document."""
        data = await self._outline_request(
            guild_id,
            "documents.list",
            {"backlinkDocumentId": document_id, "limit": limit},
        )
        if data:
            return data.get("data", [])
        return []

    async def _get_collection_info(self, guild_id: int, collection_id: str) -> dict | None:
        """Fetch collection metadata (name, color, url)."""
        data = await self._outline_request(
            guild_id, "collections.info", {"id": collection_id}
        )
        if data:
            return data.get("data")
        return None

    async def _get_collaborator_names(self, guild_id: int, collaborator_ids: list) -> list[str]:
        """Fetch user names for collaborator IDs via users.info API."""
        names = []
        for user_id in collaborator_ids[:5]:  # Limit to 5 collaborators
            data = await self._outline_request(guild_id, "users.info", {"id": user_id})
            if data and data.get("data"):
                names.append(data["data"].get("name", "Unknown"))
        return names

    # --- Content Processing ---

    def _extract_image_ids(self, text: str) -> list[str]:
        """Extract attachment UUIDs from Outline markdown images."""
        # Pattern: ![...](attachments/UUID.ext ...) or ![](attachments/UUID.ext "...")
        pattern = r"!\[[^\]]*\]\(attachments/([a-f0-9-]+)(?:\.[^)\s\"]+)?[^)]*\)"
        return re.findall(pattern, text)

    def _transform_outline_markdown(self, text: str, base_url: str) -> str:
        """Transform Outline markdown to Discord-compatible markdown."""
        # 1a. Convert document mentions to clickable links
        # Pattern: @[Name](mention://uuid/document/doc-uuid) -> [Name](<base_url/doc/doc-uuid>)
        text = re.sub(
            r"@\[([^\]|]+)(?:\s*\|\|\s*[^\]]+)?\]\(mention://[^/]+/document/([^)]+)\)",
            rf"[\1](<{base_url}/doc/\2>)",
            text,
        )

        # 1b. Convert user mentions to plain text (no link available)
        # Pattern: @[Name || Alt](mention://uuid/user/uuid) -> @Name
        text = re.sub(
            r"@\[([^\]|]+)(?:\s*\|\|\s*[^\]]+)?\]\(mention://[^)]+\)",
            r"@\1",
            text,
        )

        # 2. Remove images with optional dimension syntax
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)

        # 3. Fix internal doc links: [text](/doc/slug) -> [text](<base_url/doc/slug>)
        text = re.sub(
            r"\[([^\]]+)\]\((/doc/[^)]+)\)",
            rf"[\1](<{base_url}\2>)",
            text,
        )

        # 4. Fix attachment links: [text](attachments/uuid) -> full URL
        text = re.sub(
            r"\[([^\]]+)\]\(attachments/([^)]+)\)",
            rf"[\1](<{base_url}/api/attachments.redirect?id=\2>)",
            text,
        )

        # 5. Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)  # Max 2 consecutive newlines
        text = re.sub(r"^\s*---\s*$", "", text, flags=re.MULTILINE)  # Remove horizontal rules
        text = re.sub(r"^\\\s*$", "", text, flags=re.MULTILINE)  # Remove backslash lines

        return text.strip()

    def _truncate_content(self, content: str, max_length: int = 4000) -> str:
        """Truncate content to fit Discord embed limits, preserving whole words."""
        if len(content) <= max_length:
            return content

        # Find the last space before the limit
        truncate_at = content.rfind(" ", 0, max_length - 30)
        if truncate_at == -1:
            truncate_at = max_length - 30

        return content[:truncate_at] + "\n\n*... [document truncated]*"

    def _format_author_footer(self, names: list[str]) -> str | None:
        """Format author names for embed footer."""
        if not names:
            return None
        if len(names) == 1:
            return f"Author: {names[0]}"
        elif len(names) == 2:
            return f"Authors: {names[0]} and {names[1]}"
        else:
            return f"Authors: {', '.join(names[:-1])}, and {names[-1]}"

    # --- AI Integration ---

    async def _get_oracle_text(self, text: str, prompt: str) -> str | None:
        """Generate AI flavor text."""
        openai_key = (await self.bot.get_shared_api_tokens("openai")).get("api_key")
        if not openai_key:
            return None

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-4o-mini",
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt + text}],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        log.error(f"OpenAI API error {resp.status}: {await resp.text()}")
                        return None
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            log.error(f"OpenAI request failed: {e}")
            return None

    # --- Embed Building ---

    def _build_main_embed(
        self,
        document: dict,
        collection: dict | None,
        content: str,
        base_url: str,
        image_ids: list[str],
        author_footer: str | None,
    ) -> discord.Embed:
        """Build the main document embed."""
        # Parse collection color (hex string like "#ff0000" -> int)
        color = 0xFF2600  # default red
        if collection and collection.get("color"):
            try:
                color = int(collection["color"].lstrip("#"), 16)
            except ValueError:
                pass

        # Build title with icon if present
        icon = document.get("icon", "") or ""
        title = document.get("title", "Untitled")
        if icon:
            # Outline returns emoji shortcodes without colons (e.g., "gem" instead of ":gem:")
            # Wrap in colons if it looks like a shortcode (alphanumeric/underscore only)
            if icon.replace("_", "").isalnum() and not icon.startswith(":"):
                icon = f":{icon}:"
            title = f"{icon} {title}"

        # Build document URL
        doc_url = f"{base_url}{document.get('url', '')}"

        embed = discord.Embed(
            title=title,
            url=doc_url,
            description=content,
            color=color,
        )

        # Add images (only if document has images)
        if len(image_ids) == 1:
            embed.set_image(url=f"{base_url}/api/attachments.redirect?id={image_ids[0]}")
        elif len(image_ids) >= 2:
            embed.set_thumbnail(url=f"{base_url}/api/attachments.redirect?id={image_ids[0]}")
            embed.set_image(url=f"{base_url}/api/attachments.redirect?id={image_ids[1]}")

        # Add author footer
        if author_footer:
            embed.set_footer(text=author_footer)

        return embed

    def _build_secondary_embed(
        self, backlinks: list, search_results: list, base_url: str
    ) -> discord.Embed | None:
        """Build the secondary embed with backlinks and other results."""
        # Get backlink document IDs for deduplication
        backlink_ids = {doc.get("id") for doc in backlinks}

        # Filter search results to exclude backlinks and the primary document
        unique_results = [
            r
            for r in search_results
            if r.get("document", {}).get("id") not in backlink_ids
        ]

        fields = []

        # Backlinks section (prioritized)
        if backlinks:
            backlink_lines = []
            for doc in backlinks[:5]:
                title = doc.get("title", "Untitled")
                url = f"{base_url}{doc.get('url', '')}"
                backlink_lines.append(f"- [{title}](<{url}>)")
            fields.append(("🔗 Backlinks", "\n".join(backlink_lines)))

        # Other search results section (only show if few backlinks)
        if unique_results and len(backlinks) < 3:
            result_lines = []
            for r in unique_results[:4]:
                doc = r.get("document", {})
                title = doc.get("title", "Untitled")
                url = f"{base_url}{doc.get('url', '')}"
                result_lines.append(f"- [{title}](<{url}>)")
            if result_lines:
                fields.append(("🔎 Search Results", "\n".join(result_lines)))

        if not fields:
            return None

        embed = discord.Embed(color=0x999999)
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=True)

        return embed

    # --- Main Response Builder ---

    async def _build_lore_response(
        self, guild_id: int, query: str
    ) -> tuple[str | None, list[discord.Embed], LoreView | None]:
        """Build the complete lore response (content, embeds, view)."""
        base_url = await self.config.guild_from_id(guild_id).wiki_url()
        custom_prompt = await self.config.guild_from_id(guild_id).prompt()
        prompt = custom_prompt or DEFAULT_PROMPT

        # Search for documents
        results = await self._search_documents(guild_id, query, limit=5)

        if not results:
            # No results - return "not found" response
            custom_no_results = await self.config.guild_from_id(guild_id).no_results_prompt()
            no_results_prompt = custom_no_results or NO_RESULTS_PROMPT
            oracle_text = await self._get_oracle_text(query, no_results_prompt)

            content = None
            if oracle_text:
                content = f'*"{oracle_text}"*'

            embed = discord.Embed(
                title="Nothing is written...",
                description=f"No lore found for **{query}**.\n\nTry a different search term, or create new lore!",
                color=0xFF2600,
            )

            view = View()
            view.add_item(
                Button(
                    label="Create Lore",
                    style=discord.ButtonStyle.link,
                    url=f"{base_url}/doc/new",
                    emoji="📚",
                )
            )

            return content, [embed], view

        # Get primary document from first result
        primary_result = results[0]
        document = primary_result.get("document", {})
        other_results = results[1:]  # Remaining results for secondary embed

        # Extract data from document
        document_id = document.get("id")
        collection_id = document.get("collectionId")
        raw_content = document.get("text", "")
        collaborator_ids = document.get("collaboratorIds", [])

        # Extract image IDs before transforming markdown
        image_ids = self._extract_image_ids(raw_content)

        # Fetch additional data
        backlinks = []
        collection = None
        author_names = []

        if document_id:
            backlinks = await self._get_backlinks(guild_id, document_id, limit=5)

        if collection_id:
            collection = await self._get_collection_info(guild_id, collection_id)

        if collaborator_ids:
            author_names = await self._get_collaborator_names(guild_id, collaborator_ids)

        # Transform and truncate content
        content = self._transform_outline_markdown(raw_content, base_url)
        content = self._truncate_content(content)

        # Generate AI flavor text
        flavor_text = None
        oracle_text = await self._get_oracle_text(document.get("title", ""), prompt)
        if oracle_text:
            flavor_text = f'*"{oracle_text}"*'

        # Build author footer
        author_footer = self._format_author_footer(author_names)

        # Build embeds
        main_embed = self._build_main_embed(
            document, collection, content, base_url, image_ids, author_footer
        )
        secondary_embed = self._build_secondary_embed(backlinks, other_results, base_url)

        embeds = [main_embed]
        if secondary_embed:
            embeds.append(secondary_embed)

        # Build view
        doc_url = f"{base_url}{document.get('url', '')}"
        collection_url = f"{base_url}{collection.get('url', '')}" if collection else None
        collection_name = collection.get("name") if collection else None

        view = LoreView(
            cog=self,
            query=query,
            guild_id=guild_id,
            document_url=doc_url,
            collection_name=collection_name,
            collection_url=collection_url,
        )

        return flavor_text, embeds, view

    # --- Commands ---

    @commands.hybrid_command()
    async def lore(self, ctx: commands.Context, *, query: str) -> None:
        """Search the lore wiki for a topic.

        Example: /lore dragons
        """
        # Check for wiki URL configuration
        wiki_url = await self.config.guild(ctx.guild).wiki_url()
        if not wiki_url:
            await ctx.send(
                error("Wiki URL not configured. Use `[p]loreconfig url <url>` first."),
                ephemeral=True,
            )
            return

        # Check for API key
        outline_key = (await self.bot.get_shared_api_tokens("outline")).get("api_key")
        if not outline_key:
            await ctx.send(
                error("Outline API key not configured. Use `[p]set api outline api_key,<key>`"),
                ephemeral=True,
            )
            return

        await ctx.defer()

        try:
            content, embeds, view = await self._build_lore_response(ctx.guild.id, query)
            message = await ctx.send(content=content, embeds=embeds, view=view)
            if hasattr(view, "set_message"):
                view.set_message(message)
        except Exception as e:
            log.error(f"Lore command failed: {e}")
            await ctx.send(error(f"Failed to search lore: {e}"), ephemeral=True)

    # --- Configuration Commands ---

    @commands.group()
    @checks.is_owner()
    async def loreconfig(self, ctx: commands.Context):
        """Configure the Lore cog."""
        pass

    @loreconfig.command()
    async def settings(self, ctx: commands.Context) -> None:
        """Display current Lore settings."""
        outline_key = (await self.bot.get_shared_api_tokens("outline")).get("api_key")
        openai_key = (await self.bot.get_shared_api_tokens("openai")).get("api_key")
        wiki_url = await self.config.guild(ctx.guild).wiki_url()
        custom_prompt = await self.config.guild(ctx.guild).prompt()
        custom_no_results = await self.config.guild(ctx.guild).no_results_prompt()

        setting_list = {
            "Wiki URL": wiki_url,
            "Outline API Key": "Set" if outline_key else "Not Set",
            "OpenAI API Key": "Set" if openai_key else "Not Set (AI flavor disabled)",
            "Custom Prompt": (
                (custom_prompt[:80] + "...")
                if custom_prompt and len(custom_prompt) > 80
                else (custom_prompt or "Using default Oracle prompt")
            ),
            "No Results Prompt": (
                (custom_no_results[:80] + "...")
                if custom_no_results and len(custom_no_results) > 80
                else (custom_no_results or "Using default prompt")
            ),
        }

        embed = discord.Embed(title="📜 Lore Settings", color=0xFF0000)
        for setting, value in setting_list.items():
            embed.add_field(name=setting, value=f"```{value}```", inline=False)
        await ctx.send(embed=embed)

    @loreconfig.command()
    async def url(self, ctx: commands.Context, wiki_url: str) -> None:
        """Set the Outline wiki URL for this guild.

        Example: [p]loreconfig url https://wiki.example.com
        """
        # Strip trailing slash
        wiki_url = wiki_url.rstrip("/")
        await self.config.guild(ctx.guild).wiki_url.set(wiki_url)
        await ctx.send(success(f"Wiki URL set to `{wiki_url}`"))

    @loreconfig.command()
    async def prompt(self, ctx: commands.Context, *, prompt: str = None) -> None:
        """Set custom AI prompt for found documents. Use 'None' to reset.

        The document title will be appended to your prompt.
        """
        if prompt and prompt.lower() == "none":
            prompt = None
        await self.config.guild(ctx.guild).prompt.set(prompt)
        if prompt:
            await ctx.send(success("Custom prompt saved."))
        else:
            await ctx.send(success("Prompt reset to default Oracle of Pyora."))

    @loreconfig.command()
    async def noresults(self, ctx: commands.Context, *, prompt: str = None) -> None:
        """Set custom AI prompt for no results. Use 'None' to reset.

        The search query will be appended to your prompt.
        """
        if prompt and prompt.lower() == "none":
            prompt = None
        await self.config.guild(ctx.guild).no_results_prompt.set(prompt)
        if prompt:
            await ctx.send(success("No-results prompt saved."))
        else:
            await ctx.send(success("No-results prompt reset to default."))
