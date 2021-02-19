from enum import Enum, auto
import discord
import re

class State(Enum):
	REPORT_START = auto()
	AWAITING_MESSAGE = auto()
	MESSAGE_IDENTIFIED = auto()
	REPORT_COMPLETE = auto()
	AWAITING_COMMENTS = auto()
	AWAITING_CONFIRMATION = auto()

class Report:
	START_KEYWORD = "report"
	CANCEL_KEYWORD = "cancel"
	HELP_KEYWORD = "help"
	CONFIRM_KEYWORD = "yes"

	SPAM_KEYWORD = "spam"
	FRAUD_KEYWORD = "fraud"
	HATE_KEYWORD = "hate speech/harrasment"
	VIOLENCE_KEYWORD = "violence"
	INTIMATE_KEYWORD = "intimate materials"
	OTHER_KEYWORD = "other"

	TYPES = [SPAM_KEYWORD, FRAUD_KEYWORD, HATE_KEYWORD, VIOLENCE_KEYWORD, INTIMATE_KEYWORD, OTHER_KEYWORD]

	def __init__(self, client):
		self.state = State.REPORT_START
		self.client = client
		self.message = None
		self.reported_message = None
		self.comment = None

	async def handle_message(self, message):
		'''
		This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
		prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
		get you started and give you a model for working with Discord.
		'''


		if message.content == self.CANCEL_KEYWORD:
			self.state = State.REPORT_COMPLETE
			return ["Report cancelled."]

		if self.state == State.REPORT_START:
			reply =  "Thank you for starting the reporting process. "
			reply += "Say `help` at any time for more information.\n\n"
			reply += "Please copy paste the link to the message you want to report.\n"
			reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
			self.state = State.AWAITING_MESSAGE
			return [reply]

		if self.state == State.AWAITING_MESSAGE:
			# Parse out the three ID strings from the message link
			m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
			if not m:
				return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
			guild = self.client.get_guild(int(m.group(1)))
			if not guild:
				return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
			channel = guild.get_channel(int(m.group(2)))
			if not channel:
				return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
			try:
				message = await channel.fetch_message(int(m.group(3)))
			except discord.errors.NotFound:
				return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

			# Here we've found the message - it's up to you to decide what to do next!
			self.state = State.MESSAGE_IDENTIFIED
			self.reported_message = message
			return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
					"If this is not the right message, type `cancel` and restart to reporting process.", \
					"Otherwise, let me know which of the following abuse types this message is", \
					'`' + self.SPAM_KEYWORD + '`\n`' + self.FRAUD_KEYWORD + '`\n`' + \
					self.HATE_KEYWORD + '`\n`' + self.VIOLENCE_KEYWORD + '`\n`' + \
					self.INTIMATE_KEYWORD + '`\n`' + self.OTHER_KEYWORD + '`']

		if self.state == State.MESSAGE_IDENTIFIED:
			if message.content not in self.TYPES:
				return ["I'm sorry. That doesn't seem to match one of the options. Please try again."]
			self.type = message.content
			self.state = State.AWAITING_COMMENTS
			return ["You've identified this messages as `" + self.type + "`\nAdd any comments you'd like to send to the mods."]

		if self.state == State.AWAITING_COMMENTS:
			self.comment = message.content
			reply =  "Alright, here's the report I'm sending to the mods\n"
			reply += "`The following message was reported\n{}: {}`\n".format(self.reported_message.author.name, self.reported_message.content)
			reply += "These comments are attached `{}`\n".format(self.comment)
			reply += "Reply `yes` to send this report to the mods\n"
			reply += "Reply `cancel` to cancel the reporting process"
			self.state = State.AWAITING_CONFIRMATION
			return [ reply ]

		if self.state == State.AWAITING_CONFIRMATION:
			if message.content == self.CONFIRM_KEYWORD:
				mod_channel = self.mod_channels[message.guild.id]
				return ["Your report has been sent to the mods"]
			else:
				return ["Reply `yes` to send this report to the mods\nReply `cancel` to cancel the reporting process"]

		return []

	def report_complete(self):
		return self.state == State.REPORT_COMPLETE


	def __str__(self):
		s = 
