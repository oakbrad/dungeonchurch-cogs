"""
Functions for creating embeds
"""
import discord
from ..oracle import *

async def game_init_embed(cog, channel) -> discord.Embed:
    """Construct the initial game info embed."""
    return

def game_state_embed(self, game_state) -> discord.Embed:
    """Create the embed of the Game State tracking message."""
    embed = discord.Embed(
        title=f"🗺️ The Quiet Year: Game Tracker",
        description=f"# Week {game_state['week']} (Round {game_state['round']})",
        color=0xff0000
    )
    players = game_state["players"]
    if players:
        mention = (
            f"<@{players[0]}>" if len(players) == 1
            else f"{', '.join(f'<@{player}>' for player in players[:-1])}, and <@{players[-1]}>"
        )
    else:
        mention = "`No one has joined the game yet.`"
    embed.add_field(name="Players", value=mention, inline=False)

    # Abundances
    abundances_text = "\n".join([f"* {item}" for item in game_state["abundances"]]) or "`None`"
    embed.add_field(name="Abundances", value=abundances_text, inline=True)

    # Scarcities
    scarcities_text = "\n".join([f"* {item}" for item in game_state["scarcities"]]) or "`None`"
    embed.add_field(name="Scarcities", value=scarcities_text, inline=True)

    # Contempt Pool
    contempt_pool = f"```ansi\n[2;31m{game_state['contempt_pool']}/20[0m\n```"
    #contempt_pool = f"```arm\n{str(game_state['contempt_pool'])  }\n```"
    embed.add_field(name="Contempt",value=contempt_pool, inline=True)

    # Projects
    projects = game_state["projects"]
    projects_text = "\n".join(
        [f"* {proj['project']} [{proj['duration']} Weeks]" for proj in projects]
    ) or "`None`"
    embed.add_field(name="Projects", value=projects_text, inline=False)

    # Footer info
    timeout = game_state["round_timeout"]
    num_players = str(len(game_state["players"]))
    if not num_players:
        num_players = "0"
    embed.set_footer(text=f"👥 {num_players} Playing | ⏳ Round Time Limit: {timeout}m")
    return embed

async def update_state_embed(cog, channel, game_state) -> None:
    """Update the Game State View."""
    state_message_id = game_state.get("game_state_message")
    if not state_message_id:
        return  # No state message to update

    try:
        state_message = await channel.fetch_message(state_message_id)
        # Update the embed and view
        state_embed = game_state_embed(cog, game_state)
        await state_message.edit(embed=state_embed)
    except discord.NotFound:
        # Message no longer exists
        pass

def game_card_embed(self, card, game_state = None) -> discord.Embed:
    """Create the embed for a card."""
    value = card.value
    suit = card.suit
    try:
        int(value)
        value_abbr = value
    except ValueError:
        value_abbr = value[0]

    # Get card data from The Oracle
    card_data = oracle.get(suit, {}).get(value_abbr, {})
    options = card_data.get("options", [])
    prompt = card_data.get("prompt", None)

    # Define game_state color based on suit
    suit_colors = {
        "Spades": 0x0a1172,
        "Clubs": 0xcc5801, 
        "Diamonds": 0xfcae1e,
        "Hearts": 0x74b72e
    }
    color = suit_colors.get(suit, 0xffffff)
    if game_state is not None:
        game_state["color"] = color

    # Create the embed
    embed = discord.Embed(
            title=f":{suit.lower()}: {value} of {suit}",
            description=f"> *{prompt}*" if prompt != None else '',
            color=color
        )
    
    # Add options with mechanics
    for i, option in enumerate(options, start=1):
        option_text = f"```{option['text']}```"
        mechanics_text = ""

        # Append mechanics if they exist
        if option.get("mechanics"):
            mechanics_effects = [mech["effect"] for mech in option["mechanics"]]
            mechanics_text = "\n".join([f"* {effect}" for effect in mechanics_effects])
        
        # Combine option text with mechanics
        if len(options) == 1:
            name = ""
        else:
            name = f"Option :number_{i}:"
        embed.add_field(
            name=name,
            value=f"{option_text}\n**{mechanics_text}**" if mechanics_text else option_text,
            inline=True
        )

    return embed