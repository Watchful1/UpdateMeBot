import static


# Renders the migration messages: the bulk message to one user and the modmail
# to one subreddit. Kept free of I/O so the wording can be tested.

NAMES_SHOWN = 3


def place(name):
	"""How a subreddit is named in a message; a u_ profile reads as the author's profile."""
	return f"u/{name[2:]}'s profile" if name.lower().startswith("u_") else f"r/{name}"


def render(subreddits):
	"""(subject, body) for one user. `subreddits` are theirs, most notifications first."""
	if not subreddits:
		raise ValueError("No subreddits to render a message for")
	shown = [place(name) for name in subreddits[:NAMES_SHOWN]]
	extra = len(subreddits) - len(shown)
	if extra:
		places = f"{', '.join(shown)} and {extra} more"
	elif len(shown) == 1:
		places = shown[0]
	else:
		places = f"{', '.join(shown[:-1])} and {shown[-1]}"

	if len(subreddits) == 1:
		subject = static.MIGRATION_MESSAGE_SUBJECT_ONE.format(place=shown[0])
		there = shown[0]
	else:
		others = len(subreddits) - 1
		subject = static.MIGRATION_MESSAGE_SUBJECT_MANY.format(
			place=shown[0], others=f"{others} other subreddit{'s' if others > 1 else ''}")
		there = "these subreddits"

	body = static.MIGRATION_MESSAGE_BODY.format(places=places, there=there, link=static.MIGRATION_POST)
	return subject, body


def render_modmail(subreddit, subscribers, notifications):
	"""(subject, body) for one subreddit's moderators."""
	with_usage = notifications >= static.MODMAIL_MIN_NOTIFICATIONS
	usage = static.MODMAIL_USAGE.format(notifications=f"{notifications:,}") if with_usage else ""
	subject = static.MODMAIL_SUBJECT.format(subreddit=subreddit)
	body = static.MODMAIL_BODY.format(
		subreddit=subreddit, subscribers=f"{subscribers:,}", usage=usage,
		# "those" points back at the usage clause, so it needs that clause to be there
		those="those" if with_usage else "their", link=static.MIGRATION_POST)
	return subject, body
