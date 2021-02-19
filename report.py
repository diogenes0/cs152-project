from enum import Enum, auto
import discord
import re

class State(Enum):
	REPORT_START = auto()
	AWAITING_MESSAGE = auto()
	MESSAGE_IDENTIFIED = auto()
	AWAITING_COMMENTS = auto()
	AWAITING_CONFIRMATION = auto()
	AWAITING_MODERATION = auto()
	REPORT_COMPLETE = auto()

class Report:
	START_KEYWORD = "report"
	CANCEL_KEYWORD = "cancel"
	HELP_KEYWORD = "help"
	CONFIRM_KEYWORD = "yes"

	SPAM_KEYWORD = "spam"
	FRAUD_KEYWORD = "fraud"
	HATE_KEYWORD = "hate speech/harassment"
	VIOLENCE_KEYWORD = "violence"
	INTIMATE_KEYWORD = "intimate materials"
	OTHER_KEYWORD = "other"

	X_EMOJI = "❌"

	TYPES = [SPAM_KEYWORD, FRAUD_KEYWORD, HATE_KEYWORD, VIOLENCE_KEYWORD, INTIMATE_KEYWORD, OTHER_KEYWORD]

	def __init__(self, client, reporter):
		self.state = State.REPORT_START
		self.client = client
		self.type = None
		self.reporter = reporter
		self.reported_message = None
		self.comment = None
		self.mod_message = None

	'''
	This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
	prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
	get you started and give you a model for working with Discord.
	'''
	async def handle_message(self, message):
		if message.content == self.CANCEL_KEYWORD:
			self.state = State.REPORT_COMPLETE
			return ["Report cancelled."]
		elif self.state == State.REPORT_START:
			return await self.start_report(message)
		elif self.state == State.AWAITING_MESSAGE:
			return await self.read_message(message)
		elif self.state == State.MESSAGE_IDENTIFIED:
			return await self.get_comments(message)
		elif self.state == State.AWAITING_COMMENTS:
			return await self.confirm_report(message)
		elif self.state == State.AWAITING_CONFIRMATION:
			return await self.send_report(message)
		else:
			return []

	'''
	This function prints a message and starts the reporting flow
	'''
	async def start_report(self, message):
		reply =  "Thank you for starting the reporting process. "
		reply += "Say `help` at any time for more information.\n\n"
		reply += "Please copy paste the link to the message you want to report.\n"
		reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
		self.state = State.AWAITING_MESSAGE
		return [reply]


	'''
	This function reads a link to a discord message, parses out the message and informs the user of it
	If the message is severe enough, it is hidden pending moderation
	'''
	async def read_message(self, message):
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
		if self.client.eval_text(self.reported_message):
			await self.hide_message()
		return ["I found this message:", "```" + message.author.name + ": " + message.content + "```\n" + \
				"If this is not the right message, type `cancel` and restart to reporting process.\n" + \
				"Otherwise, let me know which of the following abuse types this message is\n" + \
				'`' + self.SPAM_KEYWORD + '`\n`' + self.FRAUD_KEYWORD + '`\n`' + \
				self.HATE_KEYWORD + '`\n`' + self.VIOLENCE_KEYWORD + '`\n`' + \
				self.INTIMATE_KEYWORD + '`\n`' + self.OTHER_KEYWORD + '`']


	'''
	This function asks the user for comments on their report
	'''
	async def get_comments(self, message):
		if message.content not in self.TYPES:
			return ["I'm sorry. That doesn't seem to match one of the options. Please try again."]
		self.type = message.content
		self.state = State.AWAITING_COMMENTS
		return ["You've identified this messages as `" + self.type + "`\nAdd any comments you'd like to send to the mods."]


	'''
	This function prints the report back to the user
	'''
	async def confirm_report(self, message):
		self.comment = message.content
		reply =  "Alright, here's the report I'm sending to the mods\n"
		reply += str(self) + "\n"
		reply += "Reply `yes` to send this report to the mods\n"
		reply += "Reply `cancel` to cancel the reporting process"
		self.state = State.AWAITING_CONFIRMATION
		return [ reply ]


	'''
	This function sends the report to the mod channel and informs the user
	'''
	async def send_report(self, message):
		if message.content == self.CONFIRM_KEYWORD:
			mod_channel = self.client.mod_channels[self.reported_message.guild.id]
			self.mod_message = await mod_channel.send(str(self))
			self.state = State.AWAITING_MODERATION
			return ["Your report has been sent to the mods"]
		else:
			return ["Reply `yes` to send this report to the mods\nReply `cancel` to cancel the reporting process"]

	'''
	This function applies the decision of the moderators to a message
	'''
	async def moderate(self, message):
		await reported_message.clear_reactions()
		await reported_message.add_reaction(self.X_EMOJI)
		self.state = State.REPORT_COMPLETE


	'''
	This function is called when a message is automatically flagged as severe enough to warrant automoderation
	'''
	async def automoderate(self, message):
		self.reporter = self.client.user
		self.reported_message = message
		self.comment = "Automatically generated report"
		mod_channel = self.client.mod_channels[self.reported_message.guild.id]
		self.mod_message = await mod_channel.send(str(self))
		await self.hide_message()

	'''
	This function temporarily hides the reported message while it is under review
	'''
	async def hide_message(self):
		await self.reported_message.clear_reactions()
		await self.reported_message.add_reaction(self.X_EMOJI) # TODO figure out emoji

	def report_complete(self):
		return self.state == State.REPORT_COMPLETE

	'''
	Having a built-in string method is nice for many reasons
	'''
	def __str__(self):
		s =  f"User `{self.reporter.name}` reported the following message from user `{self.reported_message.author.name}` as {self.type}\n"
		s += f"`{self.reported_message.content}`\n"
		s += f"The following comments are attached:\n"
		s += f"`{self.comment}`"
		return s
