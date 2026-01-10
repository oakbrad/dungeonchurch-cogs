import io
import re
import logging
from datetime import datetime
import aiohttp
import discord
from PIL import Image
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
        super().__init__(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄")
        self.cog = cog
        self.query = query
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            content, embeds, new_view, files = await self.cog._build_lore_response(
                self.guild_id, self.query
            )
            # Delete old message and send new one (edit doesn't support new attachments)
            old_message = self.view.message
            new_message = await interaction.followup.send(
                content=content, embeds=embeds, view=new_view, files=files
            )
            new_view.set_message(new_message)
            if old_message:
                try:
                    await old_message.delete()
                except discord.NotFound:
                    pass
        except Exception as e:
            log.error(f"Refresh failed: {e}")
            await interaction.followup.send(
                error("Failed to refresh lore."), ephemeral=True
            )


class SearchResultButton(Button):
    """Numbered button for search results that loads the full document."""

    def __init__(self, cog: "Lore", guild_id: int, document_id: str, index: int):
        # Number emojis for positions 1-5
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=number_emojis[index],
        )
        self.cog = cog
        self.guild_id = guild_id
        self.document_id = document_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Fetch the document by ID
            data = await self.cog._outline_request(
                self.guild_id, "documents.info", {"id": self.document_id}
            )

            if not data or not data.get("data"):
                await interaction.followup.send(
                    error("Failed to load document."), ephemeral=True
                )
                return

            document = data["data"]
            base_url = await self.cog.config.guild_from_id(self.guild_id).wiki_url()

            # Build the full lore response for this document
            collection_id = document.get("collectionId")
            document_id = document.get("id")
            raw_content = document.get("text", "")
            collaborator_ids = document.get("collaboratorIds", [])
            creator_id = document.get("createdBy", {}).get("id")
            updated_at_str = document.get("updatedAt")

            # Parse updatedAt timestamp
            updated_at = None
            if updated_at_str:
                try:
                    updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

            # Extract image IDs
            image_ids = self.cog._extract_image_ids(raw_content)

            # Fetch additional data
            backlinks = await self.cog._get_backlinks(self.guild_id, document_id, limit=5)
            collection = None
            if collection_id:
                collection = await self.cog._get_collection_info(self.guild_id, collection_id)

            author_names = await self.cog._get_collaborator_names(
                self.guild_id, collaborator_ids, creator_id
            )

            image_files = []
            if image_ids:
                image_files = await self.cog._get_image_files(self.guild_id, image_ids)

            # Transform and truncate content
            content = self.cog._transform_outline_markdown(raw_content, base_url)
            content = self.cog._truncate_content(content)

            # Generate AI flavor text
            flavor_text = None
            custom_prompt = await self.cog.config.guild_from_id(self.guild_id).prompt()
            prompt = custom_prompt or DEFAULT_PROMPT
            oracle_text = await self.cog._get_oracle_text(document.get("title", ""), prompt)
            if oracle_text:
                flavor_text = f'*"{oracle_text}"*'

            # Build author footer
            author_footer = self.cog._format_author_footer(author_names)

            # Build embeds - no search results for this view
            main_embed = self.cog._build_main_embed(
                document, collection, content, base_url, image_files, author_footer, updated_at
            )
            secondary_embed = self.cog._build_secondary_embed(backlinks, [], base_url)

            embeds = [main_embed]
            if secondary_embed:
                embeds.append(secondary_embed)

            # Build view
            doc_url = f"{base_url}{document.get('url', '')}"
            collection_url = f"{base_url}{collection.get('url', '')}" if collection else None
            collection_name = collection.get("name") if collection else None

            view = LoreView(
                cog=self.cog,
                query=document.get("title", ""),
                guild_id=self.guild_id,
                document_url=doc_url,
                collection_name=collection_name,
                collection_url=collection_url,
            )

            # Delete old message and send new one
            old_message = self.view.message
            new_message = await interaction.followup.send(
                content=flavor_text, embeds=embeds, view=view, files=image_files
            )
            view.set_message(new_message)
            if old_message:
                try:
                    await old_message.delete()
                except discord.NotFound:
                    pass

        except Exception as e:
            log.error(f"Search result button failed: {e}")
            await interaction.followup.send(
                error("Failed to load document."), ephemeral=True
            )


class SearchResultsView(View):
    """View with numbered buttons for search results."""

    def __init__(self, cog: "Lore", guild_id: int, results: list, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.message = None

        # Add numbered buttons for up to 5 results
        for i, result in enumerate(results[:5]):
            document = result.get("document", {})
            doc_id = document.get("id")
            if doc_id:
                self.add_item(SearchResultButton(cog, guild_id, doc_id, i))

    def set_message(self, message: discord.Message):
        self.message = message

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.NotFound:
                pass


class LoreView(View):
    """View containing Edit, Collection, and Refresh buttons."""

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

        # Edit button (link to document) - first
        if document_url:
            self.add_item(
                Button(
                    label="View or Edit",
                    style=discord.ButtonStyle.link,
                    url=document_url,
                    emoji="📝",
                )
            )

        # Collection button (link to collection page) - second
        if collection_url and collection_name:
            self.add_item(
                Button(
                    label=collection_name,
                    style=discord.ButtonStyle.link,
                    url=collection_url,
                    emoji="📚",
                )
            )

        # Refresh button - last
        self.add_item(RefreshButton(cog, query, guild_id))

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

    async def _get_collaborator_names(
        self, guild_id: int, collaborator_ids: list, creator_id: str | None = None
    ) -> list[str]:
        """Fetch user names for collaborator IDs via users.info API.

        Returns names with creator first (if provided), then other collaborators.
        """
        names = []
        seen_ids = set()

        # Fetch creator first if provided
        if creator_id:
            seen_ids.add(creator_id)
            data = await self._outline_request(guild_id, "users.info", {"id": creator_id})
            if data and data.get("data"):
                names.append(data["data"].get("name", "Unknown"))

        # Then fetch other collaborators (excluding creator)
        for user_id in collaborator_ids[:5]:
            if user_id in seen_ids:
                continue
            seen_ids.add(user_id)
            data = await self._outline_request(guild_id, "users.info", {"id": user_id})
            if data and data.get("data"):
                names.append(data["data"].get("name", "Unknown"))

        return names

    def _resize_image_for_discord(self, data: bytes, max_size: int = 8_000_000) -> tuple[bytes, str]:
        """Resize an image to fit within Discord's file size limit.

        Returns (image_bytes, extension).
        """
        if len(data) <= max_size:
            # Try to detect format from data
            try:
                img = Image.open(io.BytesIO(data))
                fmt = img.format.lower() if img.format else "png"
                ext = "jpg" if fmt == "jpeg" else fmt
                return data, ext
            except Exception:
                return data, "png"

        try:
            img = Image.open(io.BytesIO(data))

            # Convert RGBA to RGB for JPEG (no alpha support)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Progressively reduce size until under limit
            quality = 85
            scale = 1.0

            while True:
                output = io.BytesIO()

                # Resize if needed
                if scale < 1.0:
                    new_size = (int(img.width * scale), int(img.height * scale))
                    resized = img.resize(new_size, Image.Resampling.LANCZOS)
                else:
                    resized = img

                # Save as JPEG for better compression
                resized.save(output, format="JPEG", quality=quality, optimize=True)
                result = output.getvalue()

                if len(result) <= max_size:
                    log.debug(
                        f"Resized image: {len(data)} -> {len(result)} bytes "
                        f"(scale={scale:.2f}, quality={quality})"
                    )
                    return result, "jpg"

                # Reduce quality first, then scale
                if quality > 50:
                    quality -= 10
                elif scale > 0.3:
                    scale -= 0.1
                    quality = 85  # Reset quality when scaling down
                else:
                    # Give up and return what we have
                    log.warning(f"Could not reduce image below {len(result)} bytes")
                    return result, "jpg"

        except Exception as e:
            log.error(f"Failed to resize image: {e}")
            return data, "png"

    async def _get_image_files(
        self, guild_id: int, image_ids: list[str]
    ) -> list[discord.File]:
        """Fetch image binary data and return as discord.File objects.

        The Outline API requires auth to access images, so we fetch the binary
        data directly and pass it to Discord as file attachments.
        Images are resized if they exceed Discord's 8MB limit.
        """
        files = []
        base_url = await self.config.guild_from_id(guild_id).wiki_url()
        api_key = (await self.bot.get_shared_api_tokens("outline")).get("api_key")
        if not api_key or not base_url:
            return files

        for i, img_id in enumerate(image_ids[:2]):  # Only first 2 images
            url = f"{base_url}/api/attachments.redirect"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        headers=headers,
                        json={"id": img_id},
                        timeout=aiohttp.ClientTimeout(total=15),
                        allow_redirects=True,
                    ) as resp:
                        if resp.status == 200:
                            # Read binary data
                            data = await resp.read()

                            # Resize if needed to fit Discord limits
                            resized_data, ext = self._resize_image_for_discord(data)

                            filename = f"image{i}.{ext}"
                            files.append(discord.File(io.BytesIO(resized_data), filename=filename))
                            log.debug(f"Fetched image {img_id} as {filename} ({len(resized_data)} bytes)")
                        else:
                            log.warning(f"Failed to get image {img_id}: status {resp.status}")
            except Exception as e:
                log.error(f"Failed to fetch image {img_id}: {e}")

        return files

    # --- Content Processing ---

    def _extract_image_ids(self, text: str) -> list[str]:
        """Extract attachment UUIDs from Outline markdown images.

        Outline uses two formats for images:
        1. /api/attachments.redirect?id=UUID (in rendered content)
        2. attachments/UUID.ext (in raw markdown)
        """
        ids = []

        # Pattern 1: /api/attachments.redirect?id=UUID
        pattern1 = r"!\[[^\]]*\]\(/api/attachments\.redirect\?id=([a-f0-9-]+)[^)]*\)"
        matches1 = re.findall(pattern1, text)
        ids.extend(matches1)

        # Pattern 2: attachments/UUID.ext
        pattern2 = r"!\[[^\]]*\]\(attachments/([a-f0-9-]+)(?:\.[^)\s\"]+)?[^)]*\)"
        matches2 = re.findall(pattern2, text)
        ids.extend(matches2)

        log.debug(f"Image extraction: pattern1 found {len(matches1)}, pattern2 found {len(matches2)}")

        # Remove duplicates while preserving order
        seen = set()
        unique_ids = []
        for id in ids:
            if id not in seen:
                seen.add(id)
                unique_ids.append(id)

        log.debug(f"Extracted {len(unique_ids)} unique image IDs: {unique_ids[:5]}")
        return unique_ids

    def _fix_quote_blocks(self, text: str) -> str:
        """Fix quote blocks for Discord.

        Outline API returns quote blocks where multi-paragraph content is
        embedded with literal \\n\\n inside the > line. We need to:
        1. Find these embedded paragraphs and give each its own > prefix
        2. Add "> " (with space) between paragraphs for visual breaks

        This runs BEFORE \\n -> newline conversion.
        """
        lines = text.split("\n")
        result = []

        for line in lines:
            stripped = line.strip()

            if stripped == ">":
                # Empty quote line - convert to "> " with space for proper rendering
                result.append("> ")
            elif stripped.startswith("> \\n") or stripped == "> \\n":
                # Quote line that starts with literal \n - clean it up
                # "> \n*text*" -> "> *text*"
                content = stripped[1:].lstrip()  # Remove > and whitespace
                if content.startswith("\\n"):
                    content = content[2:].lstrip()  # Remove \n
                if content:
                    result.append(f"> {content}")
            elif stripped.startswith(">"):
                # Quote line - check for embedded \n\n paragraphs
                content = stripped[1:].lstrip()  # Remove > and leading space

                if "\\n\\n" in content:
                    # Split on paragraph breaks and give each its own >
                    # Add "> " between paragraphs for visual separation
                    paragraphs = content.split("\\n\\n")
                    for i, p in enumerate(paragraphs):
                        p = p.strip()
                        if p:
                            if i > 0:
                                # Add empty quote line before subsequent paragraphs
                                result.append("> ")
                            result.append(f"> {p}")
                elif content:
                    result.append(f"> {content}")
            else:
                result.append(line)

        return "\n".join(result)

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

        # 5. Simplify redundant URL links: [https://example.com](https://example.com) -> <https://example.com>
        # Wrap in < > to suppress Discord's auto-embed preview
        text = re.sub(
            r"\[(https?://[^\]]+)\]\(\1\)",
            r"<\1>",
            text,
        )

        # 6. Fix quote blocks BEFORE converting \n
        # Outline embeds multi-paragraph quotes with \n\n inside the > line
        # We need to ensure each paragraph within a quote gets the > prefix
        text = self._fix_quote_blocks(text)

        # 7. NOW convert literal \n sequences to actual newlines
        text = text.replace("\\n", "\n")

        # 8. Strip callout boxes (:::info, :::warning, etc. through :::)
        # These have no Discord equivalent
        text = re.sub(r"^:::.*$", "", text, flags=re.MULTILINE)

        # 9. Downgrade headers above ### to ### (Discord only renders up to ###)
        # #### -> ###, ##### -> ###, ###### -> ###
        text = re.sub(r"^#{4,}\s+", "### ", text, flags=re.MULTILINE)

        # 10. Clean up whitespace
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

    def _prepare_content_for_summary(self, text: str, max_chars: int = 2000) -> str:
        """Extract headings and initial content from article text for AI summarization.

        Args:
            text: Raw article text from Outline API
            max_chars: Maximum characters to include

        Returns:
            Cleaned plaintext with headings and content excerpt
        """
        # Extract all headings (H1-H6)
        heading_pattern = r'^#+\s+(.+)$'
        headings = re.findall(heading_pattern, text, re.MULTILINE)

        # Strip markdown formatting
        # Remove images
        cleaned = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # Remove links but keep text
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
        # Remove mentions
        cleaned = re.sub(r'@\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
        # Remove bold/italic
        cleaned = re.sub(r'\*\*([^\*]+)\*\*', r'\1', cleaned)
        cleaned = re.sub(r'\*([^\*]+)\*', r'\1', cleaned)
        # Remove code blocks
        cleaned = re.sub(r'```[^`]*```', '', cleaned, flags=re.DOTALL)
        # Remove inline code
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
        # Remove quote markers
        cleaned = re.sub(r'^\s*>\s*', '', cleaned, re.MULTILINE)
        # Remove multiple newlines
        cleaned = re.sub(r'\n\n+', '\n\n', cleaned)
        # Remove literal \n
        cleaned = cleaned.replace('\\n', '\n')

        cleaned = cleaned.strip()

        # Build result: headings first, then content
        result_parts = []

        if headings:
            result_parts.append("Article sections: " + ", ".join(headings[:10]))

        # Truncate content to fit within max_chars
        remaining_chars = max_chars - sum(len(p) for p in result_parts) - 20
        if remaining_chars > 100 and cleaned:
            content_excerpt = cleaned[:remaining_chars].strip()
            # Find last sentence/paragraph break
            for sep in ['\n\n', '. ', '\n']:
                last_break = content_excerpt.rfind(sep)
                if last_break > remaining_chars // 2:
                    content_excerpt = content_excerpt[:last_break + len(sep)]
                    break
            result_parts.append(content_excerpt)

        return "\n\n".join(result_parts)

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

    async def _get_wiki_summary(self, title: str, content: str) -> str | None:
        """Generate a one-sentence wiki-style summary with neutral tone.

        Args:
            title: Article title
            content: Prepared article content (headings + excerpt)

        Returns:
            One-sentence summary or None if API unavailable
        """
        openai_key = (await self.bot.get_shared_api_tokens("openai")).get("api_key")
        if not openai_key:
            return None

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        }

        prompt = f"""Provide a one-sentence summary in a wiki-style neutral tone for the following article.

Title: {title}

{content}

Summary:"""

        payload = {
            "model": "gpt-4o-mini",
            "max_tokens": 100,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
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
        image_files: list[discord.File],
        author_footer: str | None,
        updated_at: datetime | None,
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
            timestamp=updated_at,
        )

        # Add images using attachment:// references to uploaded files
        # First image -> main embed image, second image -> thumbnail
        if len(image_files) >= 1:
            embed.set_image(url=f"attachment://{image_files[0].filename}")
        if len(image_files) >= 2:
            embed.set_thumbnail(url=f"attachment://{image_files[1].filename}")

        # Add author footer
        if author_footer:
            embed.set_footer(text=author_footer)

        return embed

    def _build_secondary_embed(
        self, backlinks: list, search_results: list, base_url: str
    ) -> discord.Embed | None:
        """Build the secondary embed with two columns of links.

        Layout logic:
        - Each column can have up to 5 links
        - Column 1: Backlinks (prioritized)
        - Column 2: If backlinks > 5, overflow goes here; otherwise deduplicated search results
        """
        # Get backlink document IDs for deduplication
        backlink_ids = {doc.get("id") for doc in backlinks}

        # Filter search results to exclude backlinks
        unique_results = [
            r
            for r in search_results
            if r.get("document", {}).get("id") not in backlink_ids
        ]

        # Build list of backlink entries
        backlink_entries = []
        for doc in backlinks[:10]:  # Up to 10 backlinks (2 columns worth)
            title = doc.get("title", "Untitled")
            url = f"{base_url}{doc.get('url', '')}"
            backlink_entries.append(f"[{title}](<{url}>)")

        # Build list of search result entries
        search_entries = []
        for r in unique_results[:5]:
            doc = r.get("document", {})
            title = doc.get("title", "Untitled")
            url = f"{base_url}{doc.get('url', '')}"
            search_entries.append(f"[{title}](<{url}>)")

        # Nothing to show
        if not backlink_entries and not search_entries:
            return None

        embed = discord.Embed(color=0x999999)

        # Column 1: First 5 backlinks
        col1_entries = backlink_entries[:5]
        if col1_entries:
            embed.add_field(
                name="🔗 Backlinks",
                value="\n".join(col1_entries),
                inline=True,
            )

        # Column 2: Overflow backlinks OR search results
        if len(backlink_entries) > 5:
            # Backlinks overflow into column 2
            col2_entries = backlink_entries[5:10]
            embed.add_field(
                name="🔗 More Backlinks",
                value="\n".join(col2_entries),
                inline=True,
            )
        elif search_entries:
            # No overflow, show search results
            embed.add_field(
                name="🔎 Search Results",
                value="\n".join(search_entries),
                inline=True,
            )

        return embed

    async def _build_link_embed(
        self,
        guild_id: int,
        query: str,
        document: dict,
        collection: dict | None,
        author_names: list[str],
        base_url: str,
    ) -> discord.Embed:
        """Build a simplified embed with just link, optional summary, and author info.

        Args:
            guild_id: Discord guild ID
            query: User's search query
            document: Document data from Outline API
            collection: Collection metadata (name, color, url)
            author_names: List of author names (creator first, then collaborators)
            base_url: Base URL of the wiki

        Returns:
            discord.Embed: Simplified embed with title link, optional AI summary, and footer
        """
        title = document.get("title", "Untitled")
        url = f"{base_url}{document.get('url', '')}"

        # Get collection color
        color = 0xFF2600  # Default red
        if collection and "color" in collection:
            try:
                color = int(collection["color"].replace("#", ""), 16)
            except (ValueError, AttributeError):
                pass

        # Create embed with title as hyperlink
        embed = discord.Embed(
            title=title,
            url=url,
            color=color,
        )

        # Add wiki-style summary if OpenAI key is available
        raw_content = document.get("text", "")
        if raw_content:
            prepared_content = self._prepare_content_for_summary(raw_content)
            summary = await self._get_wiki_summary(title, prepared_content)
            if summary:
                embed.description = summary

        # Add author footer
        if author_names:
            footer_text = self._format_author_footer(author_names)
            embed.set_footer(text=footer_text)

        return embed

    # --- Main Response Builder ---

    async def _build_lore_response(
        self, guild_id: int, query: str
    ) -> tuple[str | None, list[discord.Embed], LoreView | None, list[discord.File]]:
        """Build the complete lore response (content, embeds, view, files)."""
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

            return content, [embed], view, []

        # Get primary document from first result
        primary_result = results[0]
        document = primary_result.get("document", {})
        other_results = results[1:]  # Remaining results for secondary embed

        # Extract data from document
        document_id = document.get("id")
        collection_id = document.get("collectionId")
        raw_content = document.get("text", "")
        collaborator_ids = document.get("collaboratorIds", [])
        creator_id = document.get("createdBy", {}).get("id")
        updated_at_str = document.get("updatedAt")

        # Parse updatedAt timestamp (ISO 8601 format)
        updated_at = None
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Extract image IDs before transforming markdown
        image_ids = self._extract_image_ids(raw_content)

        # Fetch additional data
        backlinks = []
        collection = None
        author_names = []
        image_files = []

        if document_id:
            backlinks = await self._get_backlinks(guild_id, document_id, limit=5)

        if collection_id:
            collection = await self._get_collection_info(guild_id, collection_id)

        # Get collaborator names with creator first
        author_names = await self._get_collaborator_names(
            guild_id, collaborator_ids, creator_id
        )

        # Fetch image files as binary data
        if image_ids:
            image_files = await self._get_image_files(guild_id, image_ids)

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
            document, collection, content, base_url, image_files, author_footer, updated_at
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

        return flavor_text, embeds, view, image_files

    # --- Commands ---

    @commands.hybrid_group(invoke_without_command=True)
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
            content, embeds, view, files = await self._build_lore_response(ctx.guild.id, query)
            message = await ctx.send(content=content, embeds=embeds, view=view, files=files)
            if hasattr(view, "set_message"):
                view.set_message(message)
        except Exception as e:
            log.error(f"Lore command failed: {e}")
            await ctx.send(error(f"Failed to search lore: {e}"), ephemeral=True)

    @lore.command(name="link")
    async def lore_link(self, ctx: commands.Context, *, query: str) -> None:
        """Get a quick link and summary for a lore topic.

        Returns a simplified embed with just the article link, optional AI summary,
        and author information.

        Example: /lore link dragons
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
            # Search for documents
            results = await self._search_documents(ctx.guild.id, query, limit=1)

            if not results:
                # No results found
                await ctx.send(
                    embed=discord.Embed(
                        title="Nothing is written...",
                        description=f"No lore found for **{query}**.\n\nTry a different search term, or create new lore!",
                        color=0xFF2600,
                    )
                )
                return

            # Get the top result
            primary_result = results[0]
            document = primary_result.get("document", {})

            # Extract data
            collection_id = document.get("collectionId")
            collaborator_ids = document.get("collaboratorIds", [])
            creator_id = document.get("createdBy", {}).get("id")

            # Fetch collection info and author names
            collection = None
            if collection_id:
                collection = await self._get_collection_info(ctx.guild.id, collection_id)

            author_names = await self._get_collaborator_names(
                ctx.guild.id, collaborator_ids, creator_id
            )

            # Build simplified embed
            embed = await self._build_link_embed(
                ctx.guild.id, query, document, collection, author_names, wiki_url
            )

            await ctx.send(embed=embed)

        except Exception as e:
            log.error(f"Lorelink command failed: {e}")
            await ctx.send(error(f"Failed to search lore: {e}"), ephemeral=True)

    @lore.command(name="search")
    async def lore_search(self, ctx: commands.Context, *, query: str) -> None:
        """Search for lore articles and get a list of results.

        Returns up to 5 search results with numbered buttons. Click a number
        to view the full article.

        Example: /lore search dragons
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
            # Search for documents (up to 5)
            results = await self._search_documents(ctx.guild.id, query, limit=5)

            if not results:
                # No results found
                await ctx.send(
                    embed=discord.Embed(
                        title="Nothing is written...",
                        description=f"No lore found for **{query}**.\n\nTry a different search term, or create new lore!",
                        color=0xFF2600,
                    )
                )
                return

            # Build search results embed with ordered list
            result_lines = []
            for i, result in enumerate(results[:5]):
                document = result.get("document", {})
                title = document.get("title", "Untitled")
                url = f"{wiki_url}{document.get('url', '')}"

                # Fetch collection name for this document
                collection_id = document.get("collectionId")
                collection_name = None
                if collection_id:
                    collection = await self._get_collection_info(ctx.guild.id, collection_id)
                    if collection:
                        collection_name = collection.get("name")

                # Format: "1. [Title](url) (Collection)"
                if collection_name:
                    result_lines.append(f"{i + 1}. [{title}](<{url}>) ({collection_name})")
                else:
                    result_lines.append(f"{i + 1}. [{title}](<{url}>)")

            description = "\n".join(result_lines)

            embed = discord.Embed(
                title=f"🔎 Search Results for '{query}'",
                description=description,
                color=0xFF2600,
            )
            embed.set_footer(text="Click the link to open in wiki, or click button below to place in chat")

            # Create view with numbered buttons
            view = SearchResultsView(self, ctx.guild.id, results)
            message = await ctx.send(embed=embed, view=view)
            view.set_message(message)

        except Exception as e:
            log.error(f"Lore search command failed: {e}")
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
