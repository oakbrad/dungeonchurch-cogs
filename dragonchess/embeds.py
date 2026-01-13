"""
Dragonchess - Embed Builders

Functions for creating Discord embeds for the game.
"""
import discord
from .game import DragonchessGame


def format_timeout(seconds: int) -> str:
    """Format a timeout in seconds to a human-readable string."""
    if seconds >= 86400:
        hours = seconds // 3600
        if hours >= 24:
            days = hours // 24
            return f"{days} day" if days == 1 else f"{days} days"
        return f"{hours} hours"
    elif seconds >= 3600:
        hours = seconds // 3600
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    elif seconds >= 60:
        minutes = seconds // 60
        return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
    else:
        return f"{seconds} seconds"

# Number emojis matching the buttons
NUMBER_EMOJIS = {
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
}


def format_dice(dice: list[int], highlight_threes: bool = True) -> str:
    """Format a list of dice values for display."""
    if not dice:
        return "`-`"

    formatted = []
    for d in dice:
        if highlight_threes and d == 3:
            formatted.append("**`3`**")  # Highlight 3s (they're worth 0)
        else:
            formatted.append(f"`{d}`")
    return " ".join(formatted)


def format_dice_emojis(dice: list[int]) -> str:
    """Format dice as emoji display."""
    if not dice:
        return "(no dice)"

    return " ".join(NUMBER_EMOJIS.get(d, str(d)) for d in dice)


def game_status_embed(game: DragonchessGame, guild: discord.Guild) -> discord.Embed:
    """Build the main game status embed showing scores and kept dice."""
    p1, p2 = game.players

    # Get member objects for display names
    m1 = guild.get_member(p1)
    m2 = guild.get_member(p2)
    name1 = m1.display_name if m1 else f"Player {p1}"
    name2 = m2.display_name if m2 else f"Player {p2}"

    # Player states
    state1 = game.player_states[p1]
    state2 = game.player_states[p2]
    score1 = state1.calculate_score() if state1.kept_dice else 0
    score2 = state2.calculate_score() if state2.kept_dice else 0
    kept1 = format_dice(state1.kept_dice) if state1.kept_dice else "*waiting...*"
    kept2 = format_dice(state2.kept_dice) if state2.kept_dice else "*waiting...*"

    embed = discord.Embed(
        title=f"🎲 {game.game_name}",
        description=f"# {score1}  vs  {score2}",
        color=0x9b59b6  # Purple
    )

    # Player 1 field
    embed.add_field(
        name=name1,
        value=kept1,
        inline=True
    )

    # Player 2 field
    embed.add_field(
        name=name2,
        value=kept2,
        inline=True
    )

    return embed


def dice_roll_embed(dice: list[int], player_name: str, show_instructions: bool = True) -> discord.Embed:
    """Build the embed showing the current dice roll."""
    embed = discord.Embed(
        title=f"{player_name}'s Roll",
        description=f"# {format_dice_emojis(dice)}",
        color=0x3498db  # Blue
    )
    if show_instructions:
        embed.set_footer(text="Make your choices below.")
    return embed


def winner_embed(game: DragonchessGame, guild: discord.Guild, is_bot_game: bool = False) -> discord.Embed:
    """Build the embed announcing the winner."""
    if game.is_tie:
        embed = discord.Embed(
            title="It's a Tie!",
            description="Both players scored the same.",
            color=0xf39c12  # Orange
        )
        p1, p2 = game.players
        s1 = game.get_score(p1)
        m1 = guild.get_member(p1)
        m2 = guild.get_member(p2)
        name1 = m1.display_name if m1 else f"Player {p1}"
        name2 = m2.display_name if m2 else f"Player {p2}"
        embed.add_field(
            name="Final Scores",
            value=f"**{name1}**: `{s1}`\n**{name2}**: `{s1}`",
            inline=False
        )
        if not is_bot_game:
            embed.set_footer(text="Rematch offer expires in 5 minutes.")
        return embed

    winner_member = guild.get_member(game.winner)
    loser_member = guild.get_member(game.loser)
    winner_name = winner_member.display_name if winner_member else f"Player {game.winner}"
    loser_name = loser_member.display_name if loser_member else f"Player {game.loser}"

    winner_score = game.get_score(game.winner)
    loser_score = game.get_score(game.loser)

    if game.moon_shot:
        embed = discord.Embed(
            title=f"🎉 {winner_name} Wins!",
            description=f"**Shooting the Moon!** Rolled 6-6-6-6-6 for an instant win!",
            color=0xe74c3c  # Red
        )
    else:
        embed = discord.Embed(
            title=f"🎉 {winner_name} Wins!",
            color=0x2ecc71  # Green
        )

    # Show final dice with scores
    winner_stats = getattr(game, 'winner_stats', None)
    loser_stats = getattr(game, 'loser_stats', None)

    # Format dice value, optionally with W/L record
    winner_dice = format_dice(game.get_kept_dice(game.winner))
    loser_dice = format_dice(game.get_kept_dice(game.loser))
    if winner_stats and loser_stats:
        winner_dice += f"\n{winner_stats.get('wins', 0)}W / {winner_stats.get('losses', 0)}L"
        loser_dice += f"\n{loser_stats.get('wins', 0)}W / {loser_stats.get('losses', 0)}L"

    embed.add_field(
        name=f"{winner_name}: `{winner_score}`",
        value=winner_dice,
        inline=True
    )
    embed.add_field(
        name=f"{loser_name}: `{loser_score}`",
        value=loser_dice,
        inline=True
    )

    return embed


def open_challenge_embed(challenger: discord.Member, game_name: str = "Dragonchess", timeout: int = None) -> discord.Embed:
    """Build the embed for an open challenge."""
    embed = discord.Embed(
        title=f"{game_name} Challenge!",
        description=f"**{challenger.display_name}** is looking for an opponent!\n\nClick **Accept** to play.",
        color=0x9b59b6
    )
    if timeout:
        footer_text = f"First to accept becomes the opponent. Expires in {format_timeout(timeout)}."
    else:
        footer_text = "First to accept becomes the opponent."
    embed.set_footer(text=footer_text)
    return embed


def leaderboard_embed(stats: dict, guild: discord.Guild, game_name: str = "Dragonchess") -> discord.Embed:
    """Build the leaderboard embed."""
    embed = discord.Embed(
        title=f"{game_name} Leaderboard",
        color=0xf1c40f  # Gold
    )

    if not stats:
        embed.description = "*No games played yet!*"
        return embed

    # Sort by wins descending
    sorted_stats = sorted(
        stats.items(),
        key=lambda x: (x[1].get("wins", 0), -x[1].get("losses", 0)),
        reverse=True
    )

    # Top 10
    lines = []
    for i, (user_id, data) in enumerate(sorted_stats[:10], 1):
        member = guild.get_member(int(user_id))
        name = member.display_name if member else f"User {user_id}"
        wins = data.get("wins", 0)
        losses = data.get("losses", 0)
        moons = data.get("moon_shots", 0)

        medal = ""
        if i == 1:
            medal = ""
        elif i == 2:
            medal = ""
        elif i == 3:
            medal = ""

        moon_str = f" ({moons} moon)" if moons == 1 else f" ({moons} moons)" if moons > 1 else ""
        lines.append(f"{medal}{i}. **{name}** - {wins}W / {losses}L{moon_str}")

    embed.description = "\n".join(lines)
    return embed


def stats_embed(member: discord.Member, stats: dict, game_name: str = "Dragonchess") -> discord.Embed:
    """Build the stats embed for a single player."""
    user_id = str(member.id)
    data = stats.get(user_id, {"wins": 0, "losses": 0, "moon_shots": 0})

    wins = data.get("wins", 0)
    losses = data.get("losses", 0)
    moons = data.get("moon_shots", 0)
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0

    embed = discord.Embed(
        title=f"{member.display_name}'s {game_name} Stats",
        color=0x9b59b6
    )
    embed.add_field(name="Wins", value=f"`{wins}`", inline=True)
    embed.add_field(name="Losses", value=f"`{losses}`", inline=True)
    embed.add_field(name="Win Rate", value=f"`{win_rate:.1f}%`", inline=True)
    embed.add_field(name="Moon Shots", value=f"`{moons}`", inline=True)
    embed.add_field(name="Games Played", value=f"`{total}`", inline=True)

    return embed
