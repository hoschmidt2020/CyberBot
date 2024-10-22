import discord
from discord.ui.item import Item
from dotenv import load_dotenv
import os
from discord.ext import commands
import json
import atexit

#|-------------------------- Bot Initialization ------------------------------|
load_dotenv()
token = str(os.getenv("TOKEN"))

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = discord.Bot(intents=intents)

CATEGORY_NAME = "RazorHack"
meeting_key = str(os.getenv("MEETING_TOKEN"))
challenges = [[]]
user_points = [["test", 10]]
challenge_discord_list = []
allowed_role = "CyberHogs Officers"
users_with_correct_answers = []

# Define your roles and points thresholds
roles_points = {
    "Script Kiddie": 10,   # Role name and points required for this role
    "Hacktivist": 20,
    "APT": 50,
}

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
        for index, user in enumerate(user_points):
            if user[0] == userid:
                return user, index
    return None

def change_token(token):
    os.environ["MEETING_TOKEN"] = token
    load_dotenv()
    meeting_key = str(os.getenv("MEETING_TOKEN"))
    print(f"Meeting key loaded: {meeting_key}") 
    
# Role creation and assignment
async def assign_or_create_role(guild, member, role_name, total_points):
    # Attempt to find the role within the guild
    role = discord.utils.get(guild.roles, name=role_name)

    # If the role does not exist, create it
    if role is None:
        try:
            print(f"Creating new role: {role_name}")
            role = await guild.create_role(name=role_name)
            # Optionally set role permissions, color, etc.
        except discord.Forbidden:
            print("I do not have permission to create roles.")
            return
        except discord.HTTPException:
            print("Creating role failed.")
            return

    # Check if the member already has the role
    if role not in member.roles:
        try:
            await member.add_roles(role)
            await member.send(f"Congratulations! You've been promoted to {role_name}.")
        except discord.Forbidden:
            print("I don't have permission to add roles.")
        except discord.HTTPException:
            print("Adding role failed.")

# Only add new challenges to the json when closing, avoids collisions in writing to the file
atexit.register(add_challenge_to_json)
atexit.register(add_user_points_to_json)
challenges = load_json("challenges.json")

#|-------------------------- Challenge View ----------------------------------|
class ChallengeSelect(discord.ui.Select):
    def __init__(self, options, *args, **kwargs):
        super().__init__(placeholder="Select a challenge:", max_values=1, min_values=1, options=options)
        
    async def callback(self, interaction: discord.Interaction):
        channel_ctx = user_channel_mapping[interaction.user.id]
        
        print(f"Channel context found, sending selected challenge...")
        chal = find_challenge(self.values[0])
        await channel_ctx.send(f"{chal[1]}\n")
        users_with_correct_answers = []
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
        super().__init__(timeout=6000)
        self.title = title
        self.add_item(SubmitButton(self.title))
    
    async def on_timeout(self):
        users_with_correct_answers = []
        for item in self.children:
            item.disabled = True
#|-------------------------- Token Modal ---------------------------------|
class TokenChange(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="Meeting Token"))
    
    async def callback(self, interaction: discord.Interaction):
        new_token = self.children[0].value
        change_token(new_token)
        await interaction.response.send_message("Updated meeting token...", ephemeral=True)
        
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
        challenge = [self.children[0].value, self.children[1].value, self.children[2].value, int(self.children[3].value)]
        challenges.append(challenge)
        await interaction.response.send_message(embeds=[embed], ephemeral=True)

#|-------------------------- Submission Modal ---------------------------------|
class SubmissionModal(discord.ui.Modal):
    def __init__(self, challenge_title, *args, **kwargs):
        super().__init__(title=f"Submit challenge flag...", *args, **kwargs)
        self.challenge_title = challenge_title
        self.add_item(discord.ui.InputText(label="Challenge Key", placeholder="Enter the meeting key..."))
        self.add_item(discord.ui.InputText(label="Your Answer", placeholder="Type your answer here..."))

    async def callback(self, interaction: discord.Interaction):
        chal = find_challenge(self.challenge_title)

        # Grab the meeting key and answer from the user
        user_key_input = self.children[0].value
        user_answer = self.children[1].value
        
        if user_key_input == meeting_key: # Check to see if the user inputted the correct meeting key
            if interaction.user.id not in users_with_correct_answers: # Check to see if the user submitted a correct answer already
                if(user_answer == chal[2]):
                    
                    await interaction.response.send_message(f"Your answer '{user_answer}' is correct!", ephemeral=True)
                    # Find the user from the list
                    user_info = find_user(interaction.user.id)
                    total_points = 0
                    users_with_correct_answers.append(interaction.user.id) # Add user to correct answer list

                    # If the user is already present in the list
                    if user_info is not None:
                        user_index = user_info[1]
                        # Add the challenge points to the user
                        user_points[user_index][1] += chal[3]
                        total_points += user_points[user_index]
                    else:
                        # If user not in list add a new record
                        user_points.append([interaction.user.id, chal[3]])
                        total_points = chal[3]
                        
                    # Fetch the member object
                    guild = interaction.guild
                    member = await guild.fetch_member(interaction.user.id) 

                    # Assign roles based on points
                    for role_name, points_required in roles_points.items():
                        if total_points >= points_required:
                            print("Sending to assign role...")
                            await assign_or_create_role(guild, member, role_name, total_points)
                            break
                    
                else:
                    await interaction.response.send_message(f"Your answer '{user_answer}' is incorrect...", ephemeral=True)
            else:
                    await interaction.response.send_message(f"You already submitted a correct answer...", ephemeral=True)
        else:
            await interaction.response.send_message(f"Incorrect meeting key...", ephemeral=True)

#|-------------------------- Events --------------------------------|          

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

#|-------------------------- Commands ------------------------------|

#|---- Create a Team Channel ----|
# Create a team channel
#|-----------------------------|
# Command to create a private team channel in the RazorHack category
@bot.slash_command(name="create_team", description="Create a private team channel.", guild_ids=[936403503407059014])
async def create_team_channel(ctx: discord.ApplicationContext, team_name: str):
    guild = ctx.guild

    # Find the hardcoded category 'RazorHack'
    category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    if category is None:
        await ctx.respond(f"Category '{CATEGORY_NAME}' not found.", ephemeral=True)
        return

    # Create the overwrites for permissions (only the user and bot can see initially)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),  # Hide for everyone
        ctx.author: discord.PermissionOverwrite(view_channel=True),  # Allow creator to see it
        guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True),  # Bot permission
    }

    # Create the private text channel under 'RazorHack' category
    try:
        team_channel = await guild.create_text_channel(team_name, category=category, overwrites=overwrites)
        await ctx.respond(f"Private channel '{team_name}' created in the '{CATEGORY_NAME}' category!", ephemeral=True)
    except discord.HTTPException as e:
        await ctx.respond(f"Failed to create the channel: {str(e)}", ephemeral=True)

#|---- Join a Team Channel ----|
# Join a premade team channel
#|-----------------------------|
# Command to allow a user to join an existing private team channel by name
@bot.slash_command(name= "join_team", description="Join a private team channel by providing a team name.", guild_ids=[936403503407059014])
async def join_team_channel(ctx: discord.ApplicationContext, team_name: str):
    guild = ctx.guild

    # Find the hardcoded category 'RazorHack'
    category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    if category is None:
        await ctx.respond(f"Category '{CATEGORY_NAME}' not found.", ephemeral=True)
        return

    # Look for the channel inside the 'RazorHack' category
    team_channel = discord.utils.get(guild.text_channels, name=team_name, category=category)
    if team_channel is None:
        await ctx.respond(f"No channel found with the name '{team_name}' in the '{CATEGORY_NAME}' category.", ephemeral=True)
        return

    # Add the user to the channel by updating channel permissions
    try:
        await team_channel.set_permissions(ctx.author, view_channel=True)
        await ctx.respond(f"You have been added to the team channel '{team_name}'!", ephemeral=True)
    except discord.HTTPException as e:
        await ctx.respond(f"Failed to add you to the channel: {str(e)}", ephemeral=True)

#|---- Add a Challenge ----|
# Use a modal to add a challenge to the challenge list
#|-------------------------|   
@bot.slash_command()
async def challenge_modal(ctx: discord.ApplicationContext):
    modal = add_challenge(title="Add a Challenge")

    # Check if user has the role
    if any(role.name == allowed_role for role in ctx.author.roles):
        await ctx.send_modal(modal)
    else:
        await ctx.author.send("You do not have the required role to use this command.")
    
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
@bot.command(description="Officer Use Only | Select a challenge to run.")
async def post_challenge(ctx):
    # Role that's allowed to use this command
    
    await ctx.respond("Look at your DMs...")

    user_channel_mapping[ctx.author.id] = ctx

    # Check if user has the role
    if any(role.name == allowed_role for role in ctx.author.roles):
        await ctx.author.send("Choose a challenge.", view=ChallengeView())
    else:
        await ctx.author.send("You do not have the required role to use this command.")

#|---- Change Token ----|
# Change the meeting token remotely
#|-------------------|   
@bot.command(description="Officer Use Only | Change Meeting Token")
async def meeting_token(ctx):
    user_channel_mapping[ctx.author.id] = ctx

    # Check if user has the role
    if any(role.name == allowed_role for role in ctx.author.roles):
        await ctx.send_modal(TokenChange(title="Change Meeting Token"))
    else:
        await ctx.author.send("You do not have the required role to use this command.") 

#|---- Change Token ----|
# Change the meeting token remotely
#|-------------------|   
@bot.command(description="Officer Use Only | Check the meeting token")
async def token_check(ctx):
    user_channel_mapping[ctx.author.id] = ctx

    # Check if user has the role
    if any(role.name == allowed_role for role in ctx.author.roles):
        await ctx.author.send(f"Current token: {meeting_key}")
    else:
        await ctx.author.send("You do not have the required role to use this command.") 
    

bot.run(token)
