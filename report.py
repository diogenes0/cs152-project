from enum import Enum, auto
import discord
import re
from datetime import datetime
from functools import total_ordering
import constants


class State(Enum):
	# Normal report states
	REPORT_START = auto()
	AWAITING_MESSAGE = auto()
	MESSAGE_IDENTIFIED = auto()
	AWAITING_SUBTYPE = auto()
	AWAITING_COMMENTS = auto()
	AWAITING_CONFIRMATION = auto()
	AWAITING_MODERATION = auto()
	REPORT_COMPLETE = auto()

	# Appeal states
	AWAITING_TICKET = auto()
	AWAITING_APPEAL_COMMENTS = auto()


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
		self.severity = 0
		self.actions = set()
		self.appeal = False


	'''
	This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what
	prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
	get you started and give you a model for working with Discord.
	'''
	async def handle_message(self, message):
		# This handles the normal reporting flow
		if message.content == constants.CANCEL_KEYWORD:
			self.state = State.REPORT_COMPLETE
			return ["Report cancelled."]
		elif message.content.startswith(constants.START_KEYWORD):
			return await self.start_report()
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

		# This handles the appeal flow
		elif message.content == constants.APPEAL_KEYWORD:
			return await self.begin_appeal(message)
		elif self.state == State.AWAITING_TICKET:
			return await self.get_ticket(message)
		elif self.state == State.AWAITING_APPEAL_COMMENTS:
			return await self.confirm_report(message)
		else:
			return []

	async def begin_appeal(self, message):
		self.appeal = True
		self.state = State.AWAITING_TICKET
		self.type = constants.APPEAL_KEYWORD
		self.subtype = constants.APPEAL_KEYWORD
		self.reporter = message.author
		return ["Please type your ticket number below"]

	async def get_ticket(self, message):
		for report in self.client.completed_reports + self.client.reports:
			if str(report.reported_message.id) == message.content:
				self.reported_message = report.reported_message
				self.severity = report.severity
				for action in report.actions:
					self.actions.add(action)
		reply = "You have appealed action based on the following message:\n"
		reply += f"`{self.reported_message.content}`\n"
		reply += "The following actions were taken because of this message:\n"
		for action in self.actions:
			reply += constants.user_action_to_word(action)
		reply += "Reply below with any additional comments you want to send to the mods"
		self.state = State.AWAITING_COMMENTS
		return [reply]

	'''
	This function prints a message and starts the reporting flow
	'''
	async def start_report(self):
		reply =  "Thank you for starting the reporting process. "
		reply += "Say `help` at any time for more information.\n\n"
		reply += "Please copy paste the link to the message you want to report.\n"
		reply += "If you want to report a user, paste a link to one of their messages.\n"
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
		self.type = eval[2]
		if self.severity > self.client.threshold:
			await self.hide_message()

		reply = f"I found this message: ```{message.author.name}: {message.content}```\n"
		reply += "If this is not the right message, type `cancel` and restart to reporting process.\n"
		reply += "Otherwise, let me know which of the following abuse types this message is\n"
		reply += "You can either type the full name of the category or the number next to it.\n"
		for s in [f"`{i+1}: {constants.TYPES[i]}`\n" for i in range(len(constants.TYPES))]:
			reply += s
		return [reply]

	def get_subtype_options(self):
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
		if message.content in [str(i+1) for i in range(len(constants.TYPES))]:
			self.type = constants.TYPES[int(message.content)-1]
		elif message.content not in constants.TYPES:
			return ["I'm sorry. That doesn't seem to match one of the options. Please try again."]
		else:
			self.type = message.content

		self.state = State.AWAITING_SUBTYPE
		reply = "You've identified this messages as `" + self.type + "`\n"

		reply += "Let me know which of the following abuse subtypes this message is in\n"
		reply += "You can either type the full name of the subtype or the number next to it\n"
		options = self.get_subtype_options()
		for i in range(len(options)):
			reply += f"`{i+1}: {options[i]}`\n"

		return [reply]
	'''
	This function asks the user for comments on their report
	'''
	async def get_comments(self, message):
		subtypes = self.get_subtype_options()
		if message.content in [str(i+1) for i in range(len(subtypes))]:
			self.subtype = subtypes[int(message.content)-1]
		elif message.content not in subtypes:
			return ["I'm sorry. That doesn't seem to match one of the options. Please try again."]
		else:
			self.subtype = message.content

		self.state = State.AWAITING_COMMENTS
		return ["You've further identified this messages as `" + self.subtype + "`\nAdd any comments you'd like to send to the mods."]

	'''
	This function prints the report back to the user
	'''
	async def confirm_report(self, message):
		self.comment = message.content
		reply =  "Alright, here's what I'm sending to the mods\n"
		reply += self.user_str() + "\n"
		reply += "Reply `yes` to send this report to the mods\n"
		reply += "Reply `cancel` to cancel the reporting process"
		self.state = State.AWAITING_CONFIRMATION
		return [reply]

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
		if not self.actions:
			await self.reported_message.clear_reactions()
		mod_channel = self.client.mod_channels[self.reported_message.guild.id]
		m = message.content

		if constants.MOD_U_NONE in m:
			self.actions.add(constants.MOD_U_NONE)
			await self.reported_message.clear_reactions()
			await mod_channel.send("Successfully took no action")
		if constants.MOD_LAW in m:
			self.actions.add(constants.MOD_LAW)
			await self.reported_message.add_reaction(constants.EMOJI_LAW)
			await mod_channel.send("Successfully reported to law enforcement")
		if constants.MOD_M_DEMOTE in m:
			self.actions.add(constants.MOD_M_DEMOTE)
			await self.reported_message.add_reaction(constants.EMOJI_DEMOTE)
			await mod_channel.send("Successfully demoted message")
		if constants.MOD_M_HIDE in m:
			self.actions.add(constants.MOD_M_HIDE)
			await self.reported_message.add_reaction(constants.EMOJI_HIDE)
			await mod_channel.send("Successfully hid message")
		if constants.MOD_M_SHADOW in m:
			self.actions.add(constants.MOD_M_SHADOW)
			await self.reported_message.add_reaction(constants.EMOJI_SHADOW)
			await mod_channel.send("Successfully shadowhid message")
		if constants.MOD_U_DEMOTE in m:
			self.actions.add(constants.MOD_U_DEMOTE)
			await self.reported_message.author.send("You have been demoted")
			await mod_channel.send("Successfully demoted message")
		if constants.MOD_U_HIDE in m:
			self.actions.add(constants.MOD_U_HIDE)
			await self.reported_message.author.send("You have been hidden")
			await mod_channel.send("Successfully hid user")
		if constants.MOD_U_SHADOW in m:
			self.actions.add(constants.MOD_U_SHADOW)
			await self.reported_message.author.send("You have been shadowbanned")
			await mod_channel.send("Successfully shadowbanned user")
		if constants.MOD_U_SUSPEND in m:
			self.actions.add(constants.MOD_U_SUSPEND)
			await self.reported_message.author.send("You have been suspended")
			await mod_channel.send("Successfully suspended user")
		if constants.MOD_U_BAN in m:
			self.actions.add(constants.MOD_U_BAN)
			await self.reported_message.author.send("You have been banned")
			await mod_channel.send("Successfully banned user")

	async def end_moderation(self):
		for action in self.actions:
			if action == constants.MOD_M_HIDE:
				msg = "The following message you posted has been hidden:\n"
				msg += f"`{self.reported_message.content}`\n"
				msg += "To appeal this decision, DM the bot with the word `appeal`"
				msg += f"Your ticket number is `{self.reported_message.id}`"
				await self.reported_message.author.send(msg)
			elif action == constants.MOD_U_SUSPEND:
				msg = "You have been suspended for posting the following message:\n"
				msg += f"`{self.reported_message.content}`\n"
				msg += "To appeal this decision, DM the bot with the word `appeal`"
				msg += f"Your ticket number is `{self.reported_message.id}`"
				await self.reported_message.author.send(msg)
			elif action == constants.MOD_U_BAN:
				msg = "You have been banned for posting the following message:\n"
				msg += f"`{self.reported_message.content}`\n"
				msg += "To appeal this decision, DM the bot with the word `appeal`"
				msg += f"Your ticket number is `{self.reported_message.id}`"
				await self.reported_message.author.send(msg)

		for report in self.client.reports:
			if report.reported_message.id == self.reported_message.id:
				if report.reporter != self.client.user:
					await report.reporter.send(f"Your report numbered `{report.reported_message.id}` has been moderated")
				report.state = State.REPORT_COMPLETE
				self.client.completed_reports.append(report)
		self.client.reports = [report for report in self.client.reports if not report.report_complete()]
		mod_channel = self.client.mod_channels[self.reported_message.guild.id]
		await mod_channel.send(f"Completed moderation of report `{self.reported_message.id}`. It will now be archived")


	'''
	This function is called when a message is automatically flagged as severe enough to warrant automoderation
	'''
	async def automoderate(self, message, eval):
		self.reporter = self.client.user
		self.reported_message = message
		self.comment = "Automatically generated report"
		self.state = State.AWAITING_MODERATION
		self.severity = eval[0]
		self.type = eval[1]
		self.subtype = eval[2]

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
		age = (datetime.now() - self.creation_time).total_seconds() / 3600  # Hours since report creation
		return (age + self.severity) * len(reports)

	'''
	A simple check to see if the report is done
	'''
	def report_complete(self):
		return self.state == State.REPORT_COMPLETE

	'''
	Users do not need to see the rated severity of their reports
	'''
	def user_str(self):
		if not self.appeal:
			s =  f"Report number `{self.reported_message.id}`\n"
			s += f"User `{self.reporter.name}` reported the following message from user `{self.reported_message.author.name}` as `{self.type}`, `{self.subtype}`\n"
			s += f"`{self.reported_message.content}`\n"
			s += f"The following comments are attached:\n"
			s += f"`{self.comment}`"
			return s
		else:
			s =  f"Report number `{self.reported_message.id}`\n"
			s += f"User `{self.reporter.name}` appeal appealed action against the following message from `{self.reported_message.author.name}`\n"
			s += f"`{self.reported_message.content}`\n"
			s += "The following actions were taken:\n"
			for action in self.actions:
				s += constants.user_action_to_word(action)
			s += f"The following comments are attached:\n"
			s += f"`{self.comment}`"
			return s

	'''
	Having a built-in string method is nice for many reasons
	'''
	def __str__(self):
		if not self.appeal:
			s =  f"Report number `{self.reported_message.id}`\n"
			s += f"User `{self.reporter.name}` reported the following message from user `{self.reported_message.author.name}` as `{self.type}`, `{self.subtype}`\n"
			s += f"`{self.reported_message.content}`\n"
			s += f"Rated at severity {round(self.severity, 2)}\n"
			s += f"The following comments are attached:\n"
			s += f"`{self.comment}`"
			return s
		else:
			s =  f"Report number `{self.reported_message.id}`\n"
			s += f"User `{self.reporter.name}` appeal appealed action against the following message from `{self.reported_message.author.name}`\n"
			s += f"`{self.reported_message.content}`\n"
			s += f"Rated at severity {round(self.severity, 2)}\n"
			s += "The following actions were taken:\n"
			for action in self.actions:
				s += constants.action_to_word(action)
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
