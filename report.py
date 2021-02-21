from enum import Enum, auto
import discord
import re
from datetime import datetime
from functools import total_ordering
import constants


class State(Enum):
	REPORT_START = auto()
	AWAITING_MESSAGE = auto()
	MESSAGE_IDENTIFIED = auto()
	AWAITING_SUBTYPE = auto()
	AWAITING_COMMENTS = auto()
	AWAITING_CONFIRMATION = auto()
	AWAITING_MODERATION = auto()
	REPORT_COMPLETE = auto()


@total_ordering
class Report:

	def __init__(self, client, reporter):
		self.state = State.REPORT_START
		self.client = client
		self.type = None
		self.subtype = None
		self.reporter = reporter
		self.reported_message = None
		self.comment = None
		self.mod_message = None
		self.creation_time = datetime.now()
		self.severity = None
		self.actions = []


	'''
	This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
	prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
	get you started and give you a model for working with Discord.
	'''
	async def handle_message(self, message):
		if message.content == constants.CANCEL_KEYWORD:
			self.state = State.REPORT_COMPLETE
			return ["Report cancelled."]
		elif self.state == State.REPORT_START:
			return await self.start_report(message)
		elif self.state == State.AWAITING_MESSAGE:
			return await self.read_message(message)
		elif self.state == State.MESSAGE_IDENTIFIED:
			return await self.get_subtype(message)
		elif self.state == State.AWAITING_SUBTYPE:
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
		eval = self.client.eval_text(message)
		self.severity = eval[0]
		self.type = eval[1]
		if self.severity > self.client.threshold:
			await self.hide_message()
		return ["I found this message:", "```" + message.author.name + ": " + message.content + "```\n" + \
				"If this is not the right message, type `cancel` and restart to reporting process.\n" + \
				"Otherwise, let me know which of the following abuse types this message is\n" + \
				'`' + constants.SPAM_KEYWORD + '`\n`' + constants.FRAUD_KEYWORD + '`\n`' + \
				constants.HATE_KEYWORD + '`\n`' + constants.VIOLENCE_KEYWORD + '`\n`' + \
				constants.INTIMATE_KEYWORD + '`\n`' + constants.OTHER_KEYWORD + '`']

	def get_subtype_options(self):
		subtypes = []
		if self.type == constants.SPAM_KEYWORD:
			subtypes = constants.SPAM_TYPES
		elif self.type == constants.FRAUD_KEYWORD:
			subtypes = constants.FRAUD_TYPES
		elif self.type == constants.HATE_KEYWORD:
			subtypes = constants.HATE_TYPES
		elif self.type == constants.VIOLENCE_KEYWORD:
			subtypes = constants.VIOLENCE_TYPES
		elif self.type == constants.INTIMATE_KEYWORD:
			subtypes = constants.INTIMATE_TYPES
		else:
			subtypes = constants.OTHER_TYPES
		return subtypes

	'''
	This function asks the user for the subtype of their report
	'''
	async def get_subtype(self, message):
		if message.content not in constants.TYPES:
			return ["I'm sorry. That doesn't seem to match one of the options. Please try again."]
		self.type = message.content
		self.state = State.AWAITING_SUBTYPE
		id_msg = "You've identified this messages as `" + self.type + "`\n"

		subtype_solicitation = "Let me know which of the following abuse subtypes this message is in\n"
		for subtype_keyword in self.get_subtype_options():
			subtype_solicitation += '`' + subtype_keyword + '`\n'

		return [id_msg + subtype_solicitation]
	'''
	This function asks the user for comments on their report
	'''
	async def get_comments(self, message):
		subtypes = self.get_subtype_options()

		if message.content not in subtypes:
			return ["I'm sorry. That doesn't seem to match one of the options. Please try again."]
		self.subtype = message.content
		self.state = State.AWAITING_COMMENTS
		return ["You've further identified this messages as `" + self.subtype + "`\nAdd any comments you'd like to send to the mods."]

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
		if message.content == constants.CONFIRM_KEYWORD:
			mod_channel = self.client.mod_channels[self.reported_message.guild.id]
			self.mod_message = await mod_channel.send("New report arrived")
			self.state = State.AWAITING_MODERATION
			return ["Your report has been sent to the mods"]
		else:
			return ["Reply `yes` to send this report to the mods\nReply `cancel` to cancel the reporting process"]

	'''
	This function applies the decision of the moderators to a message
	'''
	async def moderate(self, message):
		await self.reported_message.clear_reactions()
		m = message.content

		if constants.MOD_LAW in m:
			self.actions.append(constants.MOD_LAW)
			await self.reported_message.add_reaction(constants.EMOJI_LAW)
		if constants.MOD_M_DEMOTE in m:
			self.actions.append(constants.MOD_M_DEMOTE)
			await self.reported_message.add_reaction(constants.EMOJI_DEMOTE)
		if constants.MOD_M_HIDE in m:
			self.actions.append(constants.MOD_M_HIDE)
			await self.reported_message.add_reaction(constants.EMOJI_HIDE)
		if constants.MOD_M_SHADOW in m:
			self.actions.append(constants.MOD_M_SHADOW)
			await self.reported_message.add_reaction(constants.EMOJI_SHADOW)
		if constants.MOD_U_DEMOTE in m:
			self.actions.append(constants.MOD_U_DEMOTE)
			await self.reported_message.author.send("You have been demoted")
		if constants.MOD_U_HIDE in m:
			self.actions.append(constants.MOD_U_HIDE)
			await self.reported_message.author.send("You have been hidden")
		if constants.MOD_U_SHADOW in m:
			self.actions.append(constants.MOD_U_SHADOW)
			await self.reported_message.author.send("You have been shadowbanned")
		if constants.MOD_U_SUSPEND in m:
			self.actions.append(constants.MOD_U_SUSPEND)
			await self.reported_message.author.send("You have been suspended")
		if constants.MOD_U_BAN in m:
			self.actions.append(constants.MOD_U_BAN)
			await self.reported_message.author.send("You have been banned")

		for report in self.client.reports:
			if report.reported_message.id == self.reported_message.id:
				report.state = State.REPORT_COMPLETE

	'''
	This function is called when a message is automatically flagged as severe enough to warrant automoderation
	'''
	async def automoderate(self, message):
		self.reporter = self.client.user
		self.reported_message = message
		self.comment = "Automatically generated report"
		self.state = State.AWAITING_MODERATION
		eval = self.client.eval_text(message)
		self.severity = eval[0]
		self.type = eval[1]

		mod_channel = self.client.mod_channels[self.reported_message.guild.id]
		self.mod_message = await mod_channel.send("New report arrived")
		await self.hide_message()

	'''
	This function sends a new message to the mod channel.
	'''
	async def bump(self):
		mod_channel = self.client.mod_channels[self.reported_message.guild.id]
		self.mod_message = await mod_channel.send(str(self))

	'''
	This function temporarily hides the reported message while it is under review
	'''
	async def hide_message(self):
		await self.reported_message.clear_reactions()
		await self.reported_message.add_reaction(constants.EMOJI_SHADOW)

	'''
	This method generate the priority score for the report
	Since it needs the current time, it can't just be a member
	'''
	def get_priority(self):
		reports = [report for report in self.client.reports if report.reported_message.id == self.reported_message.id]
		age = (datetime.now() - self.creation_time).seconds
		return age + self.severity

	'''
	A simple check to see if the report is done
	'''
	def report_complete(self):
		return self.state == State.REPORT_COMPLETE

	'''
	Having a built-in string method is nice for many reasons
	'''
	def __str__(self):
		s =  f"User `{self.reporter.name}` reported the following message from user `{self.reported_message.author.name}` as `{self.type}`, `{self.subtype}`\n"
		s += f"`{self.reported_message.content}`\n"
		s += f"The following comments are attached:\n"
		s += f"`{self.comment}`"
		return s

	'''
	Having these methods allows us to have a total ordering and get reports in order of priority
	'''
	def __eq__(self, other):
		return self.get_priority() == other.get_priority()

	def __lt__(self, other):
		return self.get_priority() < other.get_priority()
