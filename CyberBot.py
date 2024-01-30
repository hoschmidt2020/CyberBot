import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

challenges = [
    "Challenge 1: Solve the puzzle...",
    "Challenge 2: Code a function that...",
    "Challenge 3: Find the bug in..."
    # Add more challenges as needed
]

user_channel_mapping = {}

# Using commands.Bot instead of discord.Client
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

# Replacing the on_message event with a bot.command for $hello
@bot.command(name='hello')
async def hello(ctx):
    await ctx.send('Hello!')

@bot.command(name='challenge')
async def post_challenge(ctx):
    # Role that's allowed to use this command
    allowed_role = "CyberHogs Officer"  # Replace with the actual role name

    # Check if user has the role
    if any(role.name == allowed_role for role in ctx.author.roles):
        challenges_preview = "\n".join(f"{i+1}. {challenge}" for i, challenge in enumerate(challenges))
        prompt = "Here are the available challenges:\n" + challenges_preview
        prompt += "\n\nReply with the number of the challenge you want to select."

        user_channel_mapping[ctx.author.id] = ctx.channel.id
        # Sending the list of challenges as a DM
        try:
            await ctx.author.send(prompt)
        except discord.Forbidden:
            await ctx.send("I can't send you a DM. Please check your privacy settings!")
    else:
        await ctx.send("You do not have the required role to use this command.")

@bot.event
async def on_message(message):
    # Ignore messages sent by the bot
    if message.author == bot.user:
        return

    
    # Check if the message is a DM and starts with a number
    if isinstance(message.channel, discord.DMChannel) and message.content.isdigit():
            # Check if the user has an associated channel
        if message.author.id in user_channel_mapping:
            channel_id = user_channel_mapping[message.author.id]
            challenge_number = int(message.content)

            if 0 < challenge_number <= len(challenges):
                selected_challenge = challenges[challenge_number - 1]

                # Fetch the channel and send the selected challenge
                channel = bot.get_channel(channel_id)
                if channel:
                    await channel.send(f"{message.author.mention} selected:\n{selected_challenge}")

                # Optionally, clear the mapping after use
                del user_channel_mapping[message.author.id]
            else:
                await message.author.send("Invalid challenge number.")

    # Process other bot commands
    await bot.process_commands(message)

@bot.command(name='submit')
async def submit_answer(ctx, *, answer):
    if ctx.guild is not None:  # Check if the command is used in a server
        await ctx.send("Please send me this submission in a DM!") 
        return

    # Code to check the answer and respond
    if answer is not None:  # You'll need to implement the check_answer logic
        await ctx.author.send("Correct answer!")
    else:
        await ctx.author.send("Try again!")

bot.run('MTIwMDgzOTA0NTkyODk4NDY0Ng.GM8RD1.BoeUCO3v1fYOXYfOG9dq0TW77lW1Tg5gEeJrjY')