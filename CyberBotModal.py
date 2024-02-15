import discord
from discord.ui.item import Item
import dotenv
import os
from discord.ext import commands
import json
import atexit

#|-------------------------- Bot Initialization ------------------------------|
dotenv.load_dotenv()
token = str(os.getenv("TOKEN"))

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = discord.Bot(intents=intents)

meeting_key = "Lab_Talk!"
challenges = [[]]
user_points = [["test", 10]]
challenge_discord_list = []

user_channel_mapping = {}

# Load the challenges from the json
def load_json(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error with file: {e}")

# Add the new challenges to the json on close
def add_challenge_to_json():
    try:
        with open('challenges.json', 'w') as file:
            json.dump(challenges, file, indent=4)
        print("New challenges saved to json")
    except Exception as e:
        print(f"Error with file: {e}")

# Add the user_points to the json on close
def add_user_points_to_json():
    try:
        with open('user_points.json', 'w') as file:
            json.dump(user_points, file, indent=4)
        print("User points added to json.")
    except Exception as e:
        print(f"Error with file: {e}")

# Process challenges into local program list from JSON
def process_challenges():
    # Check if there are new challenges to add
    if len(challenge_discord_list) < len(challenges):
        # Start from where the last challenge was added
        start_index = len(challenge_discord_list)
        for i in range(start_index, len(challenges)):
            challenge_discord_list.append(discord.SelectOption(label=challenges[i][0], description=challenges[i][1]))
    print("New challenge added.")
    return challenge_discord_list

# Find a challenge given the title
def find_challenge(challenge_title):
    for challenge in challenges:
        if challenge[0] == challenge_title:
            return challenge
    return None

# Find the user point given ID
def find_user(userid):
    if(user_points is not None):
        for user in user_points:
            if user[0] == userid:
                return user, user.index
    return None

# Only add new challenges to the json when closing, avoids collisions in writing to the file
atexit.register(add_challenge_to_json)
atexit.register(add_user_points_to_json)
challenges = load_json("challenges.json")

#|-------------------------- Challenge View ----------------------------------|
class ChallengeSelect(discord.ui.Select):
    def __init__(self, options, *args, **kwargs):
        super().__init__(placeholder="Select a challenge:", max_values=1, min_values=1, options=options)
        
    async def callback(self, interaction: discord.Interaction): # the function called when the user is done selecting options
        channel_ctx = user_channel_mapping[interaction.user.id]
        
        print(f"Channel context found, sending selected challenge...")
        chal = find_challenge(self.values[0])
        await channel_ctx.send(f"{self.values[0]} selected...\n{chal[1]}")
        await channel_ctx.send(view=SubmitView(self.values[0]))

class ChallengeView(discord.ui.View):
    def __init__(self, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.add_item(ChallengeSelect(process_challenges()))

#|-------------------------- Button View ---------------------------------|
class SubmitButton(discord.ui.Button):
    def __init__(self, title, *args, **kwargs):
        super().__init__(label="Press when ready to submit!", style=discord.ButtonStyle.green)
        self.title = title
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SubmissionModal(self.title))

class SubmitView(discord.ui.View):
    def __init__(self, title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.add_item(SubmitButton(self.title))
        
#|-------------------------- Challenge Modal ---------------------------------|
class add_challenge(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Challenge Name"))
        self.add_item(discord.ui.InputText(label="Challenge Description", style=discord.InputTextStyle.long))
        self.add_item(discord.ui.InputText(label="Answer"))
        self.add_item(discord.ui.InputText(label="Points"))

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="New Challenge Created")
        embed.add_field(name="Challenge Name", value=self.children[0].value)
        embed.add_field(name="Challenge Description", value=self.children[1].value)
        embed.add_field(name="Answer", value=self.children[2].value)
        embed.add_field(name="Points", value=self.children[3].value)

        # Create a list of challenge attributes and add it to the list
        challenge = [self.children[0].value, self.children[1].value, self.children[2].value, self.children[3].value]
        challenges.append(challenge)
        await interaction.response.send_message(embeds=[embed], ephemeral=True)

#|-------------------------- Submission Modal ---------------------------------|
class SubmissionModal(discord.ui.Modal):
    def __init__(self, challenge_title, *args, **kwargs):
        super().__init__(title=f"Submit your answer for {challenge_title}", *args, **kwargs)
        self.challenge_title = challenge_title
        self.add_item(discord.ui.InputText(label="Challenge Key", placeholder="Enter the meeting key..."))
        self.add_item(discord.ui.InputText(label="Your Answer", placeholder="Type your answer here..."))

    async def callback(self, interaction: discord.Interaction):
        chal = find_challenge(self.challenge_title)

        # Grab the meeting key and answer from the user
        user_key_input = self.children[0].value
        user_answer = self.children[1].value

        # Check to see if the user inputted the correct meeting key
        if user_key_input == meeting_key:
            if(user_answer == chal[2]):
                await interaction.response.send_message(f"Your answer '{user_answer}' is correct!", ephemeral=True)
                # Find the user from the list
                user_info = find_user(interaction.user.id)
                # If the user is already present in the list
                if user_info is not None:
                    # Add the challenge points to the user
                    user_points[user_info[1]] += chal[3]
                else:
                    # If user not in list add a new record
                    user_points.append([interaction.user.id, chal[3]])
                    
            else:
                await interaction.response.send_message(f"Your answer '{user_answer}' is incorrect...", ephemeral=True)
        else:
            await interaction.response.send_message(f"Incorrect meeting key...", ephemeral=True)

#|-------------------------- Events --------------------------------|          

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

#|-------------------------- Commands ------------------------------|

#|---- Add a Challenge ----|
# Use a modal to add a challenge to the challenge list
#|-------------------------|   
@bot.slash_command()
async def challenge_modal(ctx: discord.ApplicationContext):
    modal = add_challenge(title="Add a Challenge")
    await ctx.send_modal(modal)

#|---- Hello ----|
# Returns a warm welcome from the bot
#|---------------|   
@bot.command(name= "hello", description = "The bot says hi")
async def hello(ctx):
    await ctx.respond("Hey!")

#|---- Ping ----|
# Returns the current ping of the bot
#|---------------|   
@bot.command(description="Sends the bot's latency.")
async def ping(ctx):
    await ctx.respond(f"Pong! Latency is {bot.latency}")

#|---- Challenge ----|
# Challenge selection menu
#|-------------------|   
@bot.command(description="Select a challenge to run.")
async def post_challenge(ctx):
    # Role that's allowed to use this command
    allowed_role = "CyberHogs Officer"  # Replace with the actual role name
    await ctx.respond("Look at your DMs...")

    user_channel_mapping[ctx.author.id] = ctx

    # Check if user has the role
    if any(role.name == allowed_role for role in ctx.author.roles):
        await ctx.author.send("Choose a challenge.", view=ChallengeView())
    else:
        await ctx.author.send("You do not have the required role to use this command.")

bot.run(token)