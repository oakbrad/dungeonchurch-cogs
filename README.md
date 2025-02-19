<p align="center">
    <img width="650" src="logo-chrome-red.png">
</p>

# Dungeon Church Cogs
[Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot/releases) cogs for [Dungeon Church](https://www.dungeon.church).

Focused on RPG, D&D, & game related cogs - ideas or pull requests welcome.

----
To add these cogs to your instance, run this command first (`[p]` is your bot prefix):

```
[p]repo add dungeonchurch https://github.com/oakbrad/dungeonchurch-cogs
```

Then install your cog(s) of choice:

```
[p]cog install dungeonchurch <cog_name>
```

Finally, load your cog(s):

```
[p]load <cog_name>
```

For cogs that have LLM integration, set the OpenAPI key in Red:

```
[p]set api openai api_key,<paste here>
```

# Cogs
## augury
A simple roller that transforms into a customizable NPC when you add an OpenAI API key.
* `/augury` make an appeal to the gods
* `/augur` to change settings
## 🔒 churchmod
Automation and moderation for our private server.
## dice
Forked from [PCXCogs](https://github.com/PhasecoreX/PCXCogs). I added better formatting and commands useful for RPG players, including contested rolls.
* `/roll` roll complicated [dice formulas](https://github.com/StarlitGhost/pyhedrals)
* `/qr [mod] [@challenge]` quick roll 1d20
* `/adv [mod]` quick roll 2d20dl
* `/dis [mod]` quick roll 2d20dh
* `/randstats` roll ability scores within a set range
* `/flipcoin` flip a coin, get heads or tails
* `/eightball` ask the Magic 8 Ball
* `/diceset` to change settings
## randomstatus
Make a list of status activities, then cycle through them randomly or sequentially at a set interval.
* `/randomstatus` to change settings