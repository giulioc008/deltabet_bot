import asyncio
from pyrogram import Client, Filters, InlineKeyboardButton, Message
from pyrogram.errors import FloodWait
import re
from res.configurations import Configurations


data_frame = None


async def chat_button(client: Client, chat: dict, connection: Connection) -> InlineKeyboardButton:
	"""
		A coroutine that creates an InlineKeyboardButton form tha data of a chat
		:param client: The application
		:param chat: The chat's data
		:return: InlineKeyboardButton
	"""
	if chat["username"] is not None:
		invite_link = "https://t.me/{}".format(chat["username"])
	elif chat["invite_link"] is not None:
		invite_link = chat["invite_link"]
	else:
		# Generating the new invite_link
		invite_link = await client.export_chat_invite_link(chat["id"])

		# Saving the new invite_link
		with connection.cursor() as cursor:
			cursor.execute("UPDATE `Chats` SET `invite_link`=%(invite_link)s WHERE `id`=%(id)s;", {
				"id": chat["id"],
				"invite_link": invite_link
			})
		connection.commit()

	return InlineKeyboardButton(text=chat["title"], url=invite_link)


def int_to_str(number: int) -> str:
	"""
		A function that converts a number in its string form.
		:param number: The number to convert
		:return: str
	"""
	groups_length = 3
	number = str(number)
	start = len(number) % 3

	# Retrieving the first group
	converted_price = number[: start]

	# Retrieving the others groups
	for i in range(start, len(number), groups_length):
		converted_price += "{}{}".format("." if converted_price != "" else "", number[i : i + groups_length])

	return converted_price


async def monitors_matches(client: Client):
	# Monitors the soccer matches
	global data_frame

	parameters = {
		"token": "523daf930b89e47e",
		"type": "inplay",
		"columns": "asian,goalLine,dangerousAttacks,shotOn,shotOff"
	}

	response = requests.get(url="https://api.totalcorner.com/v1/match/today", params=parameters)
	response.raise_for_status()

	datas = response.json()
	for row in datas["data"]:
		# Removes unnecessary attributes
		row.pop("id", None)
		row.pop("ap", None)
		row.pop("h_id", None)
		row.pop("a_id", None)
		row.pop("l_id", None)
		row.pop("start", None)
		row.pop("hc", None)
		row.pop("ac", None)
		row.pop("hrc", None)
		row.pop("arc", None)
		row.pop("hyc", None)
		row.pop("ayc", None)
		row.pop("hf_hc", None)
		row.pop("hf_ac", None)
		row.pop("hf_hg", None)
		row.pop("hf_ag", None)
		row.pop("ish", None)
		row.pop("i_asian", None)
		row.pop("i_goal", None)
		row.pop("dang_attacks_h", None)
		row.pop("shot_on_h", None)
		row.pop("shot_off_h", None)

		# Rename the necessary attributes
		row["minute"] = row.pop("status")

		row["league"] = row.pop("l")

		row["hometeam"] = row.pop("h")

		row["awayteam"] = row.pop("a")

		try:
			row["hometeamGoal"] = int(row.pop("hg"))
		except ValueError:
			row["hometeamGoal"] = 0

		try:
			row["awayteamGoal"] = int(row.pop("ag"))
		except ValueError:
			row["awayteamGoal"] = 0

		row["dangerous_attacks"] = row.pop("dang_attacks")

		row["handicap"] = row.pop("p_asian")
		row["handicap"] = row["handicap"][0].split(",")
		row["handicap"] = list(map(lambda n: n.strip(), row["handicap"]))

		row["goal_line"] = row.pop("p_goal")
		row["goal_line"] = row["goal_line"][0].split(",")
		row["goal_line"] = list(map(lambda n: n.strip(), row["goal_line"]))

		row["shotOn"] = row.pop("shot_on")

		row["shotOff"] = row.pop("shot_off")

		row["bet"] = ""

		# Convert parameters from strings to numbers
		row["goal_line"] = list(map(lambda n: res.str_to_float(n), row["goal_line"]))
		if len(row["goal_line"]) == 0:
			row["goal_line"] = 0.0
		elif len(row["goal_line"]) == 1:
			row["goal_line"] = row["goal_line"].pop(0)
		elif len(row["goal_line"]) > 1:
			a = functools.reduce(lambda x, y: x + y, row["goal_line"])
			row["goal_line"] = a / float(len(row["goal_line"]))

		row["handicap"] = list(map(lambda n: res.str_to_float(n), row["handicap"]))
		if len(row["handicap"]) == 0:
			row["handicap"] = 0.0
		elif len(row["handicap"]) == 1:
			row["handicap"] = row["handicap"].pop(0)
		elif len(row["handicap"]) > 1:
			a = functools.reduce(lambda x, y: x + y, row["goal_line"])
			row["handicap"] = a / float(len(row["handicap"]))

		row["shotOn"] = list(map(lambda n: res.str_to_float(n), row["shotOn"]))

		row["minute"] = res.str_to_float(row["minute"])

		row["dangerous_attacks"] = list(map(lambda n: res.str_to_float(n), row["dangerous_attacks"]))

		row["shotOff"] = list(map(lambda n: res.str_to_float(n), row["shotOff"]))

	# Creation of the DataFrame
	df = pandas.DataFrame(data=datas["data"])

	# Creation of the DataFrame with filtered games
	df_filtered = pandas.DataFrame(data=list())
	for i in range(df.shape[0]):
		if df.at[i, "goal_line"] > 3.0 and (df.at[i, "handicap"] < -1.0 or df.at[i, "handicap"] > 1.0):
			favourite = 0
			if df.at[i, "handicap"] > 1.0:
				favourite = 1
			if df.at[i, "shotOff"][favourite] + df.at[i, "shotOn"][favourite] >= 3.0 and df.at[i, "shotOn"][favourite] >= 1.0 and df.at[i, "dangerous_attacks"][favourite] >= 2 / 3 * (df.at[i, "dangerous_attacks"][0] + df.at[i, "dangerous_attacks"][1]):
				df_filtered = df_filtered.append(df.iloc[i, :], ignore_index=True)

	# Data processing and, if applicable, reporting of the matches
	index = range(df_filtered.shape[0])

	if data_frame.empty is False:
		index = list()
		i = data_frame.eq(df_filtered)
		for j in range(i.shape[0]):
			if i.at[j, "league"] is False or i.at[j, "hometeam"] is False or i.at[j, "awayteam"] is False or i.at[j, "hometeamGoal"] is False or i.at[j, "awayteamGoal"] is False or i.at[j, "dangerous_attacks"] is False or i.at[j, "handicap"] is False or i.at[j, "goal_line"] is False or i.at[j, "shotOn"] is False or i.at[j, "shotOff"] is False:
				index.append(j)

	for i in index:
		if df_filtered.at[i, "minute"] == 10 and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 0:
			df_filtered.at[i, "bet"] = "Over 0.5 HT"
		elif df_filtered.at[i, "minute"] == 15 and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] <= 1:
			if df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 0:
				df_filtered.at[i, "bet"] = "Over 0.5 HT"
			elif df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 1:
				df_filtered.at[i, "bet"] = "Over 1.5 HT"
		elif df_filtered.at[i, "minute"] == 22 and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] <= 2:
			if df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 0:
				df_filtered.at[i, "bet"] = "Over 0.5 HT"
			elif df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 1:
				df_filtered.at[i, "bet"] = "Over 1.5 HT"
			elif df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 2:
				df_filtered.at[i, "bet"] = "Over 2.5 HT"
		elif df_filtered.at[i, "minute"] == 30 and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] <= 3:
			if df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 0:
				df_filtered.at[i, "bet"] = "Over 0.5 HT"
			elif df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 1:
				df_filtered.at[i, "bet"] = "Over 1.5 HT"
			elif df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 2:
				df_filtered.at[i, "bet"] = "Over 2.5 HT"
			elif df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] == 3:
				df_filtered.at[i, "bet"] = "Over 3.5 HT"

		await client.send_message(" ... ", "SIGNAL - {} Minutes: {}\'\n{} {} - {}\n{} Ris: {} - {}\n{} Bet: {}".format(Emoji.TWO_O_CLOCK, df_filtered.at[i, "minute"], Emoji.GLOBE_SHOWING_EUROPE_AFRICA, df_filtered.at[i, "hometeam"], df_filtered.at[i, "awayteam"], Emoji.SOCCER_BALL, df_filtered.at[i, "hometeamGoal"], df_filtered.at[i, "awayteamGoal"], Emoji.BALLOT_BOX_WITH_CHECK, df_filtered.at[i, "bet"]))

		if (df_filtered.at[i, "minute"] == 10 or df_filtered.at[i, "minute"] == 15 or df_filtered.at[i, "minute"] == 22) and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] >= 3:
			await client.send_message(" ... ", "Remove the bet.")
		elif df_filtered.at[i, "minute"] >= 45:
			if (df_filtered.at[i, "bet"] == "Over 0.5 HT" and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"]) >= 1 or (df_filtered.at[i, "bet"] == "Over 1.5 HT" and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] >= 2) or (df_filtered.at[i, "bet"] == "Over 2.5 HT" and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] >= 3) or (df_filtered.at[i, "bet"] == "Over 3.5 HT" and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] >= 4):
				await client.send_message(" ... ", "SIGNAL - {} Minutes: {}\'\n{} {} - {}\n{} Ris: {} - {}\n{} Bet: {}".format(Emoji.TWO_O_CLOCK, df_filtered.at[i, "minute"], Emoji.GLOBE_SHOWING_EUROPE_AFRICA, df_filtered.at[i, "hometeam"], df_filtered.at[i, "awayteam"], Emoji.SOCCER_BALL, df_filtered.at[i, "hometeamGoal"], df_filtered.at[i, "awayteamGoal"], Emoji.WHITE_HEAVY_CHECK_MARK, df_filtered.at[i, "bet"]))
			elif (df_filtered.at[i, "bet"] == "Over 0.5 HT" and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"]) < 1 or (df_filtered.at[i, "bet"] == "Over 1.5 HT" and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] < 2) or (df_filtered.at[i, "bet"] == "Over 2.5 HT" and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] < 3) or (df_filtered.at[i, "bet"] == "Over 3.5 HT" and df_filtered.at[i, "hometeamGoal"] + df_filtered.at[i, "awayteamGoal"] < 4):
				await client.send_message(" ... ", "SIGNAL - {} Minutes: {}\'\n{} {} - {}\n{} Ris: {} - {}\n{} Bet: {}".format(Emoji.TWO_O_CLOCK, df_filtered.at[i, "minute"], Emoji.GLOBE_SHOWING_EUROPE_AFRICA, df_filtered.at[i, "hometeam"], df_filtered.at[i, "awayteam"], Emoji.SOCCER_BALL, df_filtered.at[i, "hometeamGoal"], df_filtered.at[i, "awayteamGoal"], Emoji.CROSS_MARK, df_filtered.at[i, "bet"]))

	data_frame = df_filtered.copy()


def str_to_int(number: str) -> int:
	"""
		A function that converts a number in its integer form.
		:param number: The number to convert
		:return: int
	"""
	match = re.findall("^((\d+)\.?(\d+)?\.?(\d+)?\.?(\d+)?)(k*)$", number, re.MULTILINE | re.IGNORECASE | re.UNICODE)

	# Checking if the string have the correct syntax
	if match is False:
		return -1

	# Retrieving the match
	match = match.pop(0)
	match = list(match)

	# Determine the number
	number = int(match[0].replace(".", "")) * math.pow(10, len(match[-1]) * 3)
	number = int(number)

	return number


def str_to_float(number: str) -> float:
	"""
		A function that converts a number in its floating form.
		:param number: The number to convert
		:return: float
	"""
	try:
		return float(number)
	except (TypeError, ValueError):
		return 0.0


async def split_edit_text(config: Configurations, message: Message, text: str, **options):
	"""
		A coroutine that edits the text of a message; if text is too long sends more messages.
		:param message: Message to edit
		:param text: Text to insert
		:return: None
	"""
	await message.edit_text(text[: config.get("message_max_length")], options)
	if len(text) >= config.get("message_max_length"):
		for i in range(1, len(text), config.get("message_max_length")):
			try:
				await message.reply_text(text[i : i + config.get("message_max_length")], options, quote=True)
			except FloodWait as e:
				await asyncio.sleep(e.x)


async def split_reply_text(config: Configurations, message: Message, text: str, **options):
	"""
		A coroutine that reply to a message; if text is too long sends more messages.
		:param message: Message to reply
		:param text: Text to insert
		:return: None
	"""
	await message.reply_text(text[: config.get("message_max_length")], options)
	if len(text) >= config.get("message_max_length"):
		for i in range(1, len(text), config.get("message_max_length")):
			try:
				await message.reply_text(text[i : i + config.get("message_max_length")], options)
			except FloodWait as e:
				await asyncio.sleep(e.x)


def unknown_filter(config: Configurations):
	def func(flt, message: Message):
		text = message.text
		if text:
			message.matches = list(flt.p.finditer(text)) or None
			if message.matches is False and text.startswith("/") is True and len(text) > 1:
				return True
		return False

	commands = list(map(lambda n: n["name"], config.get("commands")))

	return Filters.create(func, "UnknownFilter", p=re.compile("/{}".format("|/".join(commands)), 0))
