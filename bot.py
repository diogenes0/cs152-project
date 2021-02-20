# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
import constants
from report import Report
from unidecode import unidecode

def make_mod_help():
    mod_help =  "Type `next` to see the next report\n"
    mod_help += "Type `help` to see this message\n"
    mod_help += "Reply directly to a report to moderate it\n"
    mod_help += "Here are your options moderating a report\n"
    mod_help += "`law`        incident is reported to law enforcement\n"
    mod_help += "`m_demote`   message is demoted in search\n"
    mod_help += "`m_hide`     message is hidden on platform. No user can access it\n"
    mod_help += "`m_shadow`   message is hidden from world. Available to poster\n"
    mod_help += "`u_demote`   user is demoted in search and recommendations\n"
    mod_help += "`u_hide`     user is hidden in search and recommendations\n"
    mod_help += "`u_shadow`   user is shadowbanned. Nothing they do is visible to anyone but them\n"
    mod_help += "`u_suspend`  users is suspended from platform temporarily\n"
    mod_help += "`u_ban`      user is banned from platform. account is deactivated\n"
    mod_help += "`none`       no action is taken\n"

class ModBot(discord.Client):
    def __init__(self, key):
        intents = discord.Intents.default()
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = [] # List of reports
        self.perspective_key = key
        self.threshold = 0.5 # threshold to auto-hide a message
        self.mod_help = make_mod_help() # makes mod help message

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs).
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel.
        '''

        if message.content == "$CLEAR_THIS_CHANNEL_REALLY":
            await message.channel.purge()

        # Ignore messages from us
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def on_message_edit(self, before, after):
        await self.on_message(after)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == constants.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author = message.author
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author not in [report.reporter for report in self.reports] and not message.content.startswith(constants.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author not in [report.reporter for report in self.reports]:
            self.reports.append(Report(self, author))

        # Finds the report belonging to author
        # Note that each client can only have one report
        report_index = None
        for i in range(len(self.reports)):
            if self.reports[i].reporter == author:
                report_index = i
                break

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[report_index].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[report_index].report_complete():
            self.reports.pop(report_index)


    async def handle_mod_message(self, message):
        # remove completed reports
        self.reports = [report for report in self.reports if not report.report_complete()]

        if message.content == "help":
            return await message.channel.send(self.mod_help)

        if message.reference != None:
            for report in self.reports:
                if message.reference.message_id == report.mod_message.id:
                    return await report.moderate(message)

        if message.content == "next":
            if not self.reports:
                return await message.channel.send("There are no reports to moderate")
            self.reports.sort(reverse=True)
            return await self.reports[0].bump()

    async def handle_channel_message(self, message):
        # Allow the bot to take input from the mods
        if message.channel.name == f'group-{self.group_num}-mod':
            return await self.handle_mod_message(message)

        # Don't handle messages not sent in the "group-#" channel
        if message.channel.name == f'group-{self.group_num}':
            await self.moderate_message(message)

    async def moderate_message(self, message):
        if self.eval_text(message)[0] > self.threshold:
            report = Report(self, self.user)
            await report.automoderate(message)
            self.reports.append(report)

    def eval_text(self, message):
        '''
        Given a message, forwards the message to Perspective and returns a dictionary of scores.
        '''
        PERSPECTIVE_URL = 'https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze'

        url = PERSPECTIVE_URL + '?key=' + self.perspective_key
        data_dict = {
            'comment': {'text': message.content},
            'languages': ['en'],
            'requestedAttributes': {
                                    'SEVERE_TOXICITY': {}, 'PROFANITY': {},
                                    'IDENTITY_ATTACK': {}, 'THREAT': {},
                                    'TOXICITY': {}, 'FLIRTATION': {}
                                },
            'doNotStore': True
        }
        response = requests.post(url, data=json.dumps(data_dict))
        response_dict = response.json()

        scores = {}
        for attr in response_dict["attributeScores"]:
            scores[attr] = response_dict["attributeScores"][attr]["summaryScore"]["value"]

        if "fuck" in unidecode(message.content):
            return (1, constants.OTHER_KEYWORD)
        return (0, constants.OTHER_KEYWORD)

    def code_format(self, text):
        return "```" + text + "```"

    async def on_member_join(self, member):
        print(f"{member.name} joined the channel!")
        await member.send("Welcome the the channel!")


def main():
	# Set up logging to the console
	logger = logging.getLogger('discord')
	logger.setLevel(logging.DEBUG)
	handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
	handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
	logger.addHandler(handler)

	# There should be a file called 'token.json' inside the same folder as this file
	token_path = 'tokens.json'
	if not os.path.isfile(token_path):
	    raise Exception(f"{token_path} not found!")
	with open(token_path) as f:
	    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
	    tokens = json.load(f)
	    discord_token = tokens['discord']
	    perspective_key = tokens['perspective']

	# Create and run bot
	client = ModBot(perspective_key)
	client.run(discord_token)


if __name__ == "__main__":
	main()
