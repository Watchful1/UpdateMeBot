import static


# Renders the bulk migration message for one user. `subreddits` is every
# affected subreddit for them, most active first; the message names the first
# NAMES_SHOWN and counts the rest.

NAMES_SHOWN = 3


def render(subreddits, opted_out):
	"""(subject, body). opted_out is a set of lowercase subreddit names."""
	if not subreddits:
		raise ValueError("No subreddits to render a message for")
	shown = [f"r/{name}" for name in subreddits[:NAMES_SHOWN]]
	extra = len(subreddits) - len(shown)
	if extra:
		listed = f"{', '.join(shown)} and {extra} more"
	elif len(shown) == 1:
		listed = shown[0]
	else:
		listed = f"{', '.join(shown[:-1])} and {shown[-1]}"

	# Opted-out moderators asked not to be pointed at again: drop the "yet" and
	# the install ask when every subreddit in the message opted out.
	all_opted_out = all(name.lower() in opted_out for name in subreddits)
	single = len(subreddits) == 1
	if single:
		which, there = f"r/{subreddits[0]}", "there"
		hasnt = "hasn't" if all_opted_out else "hasn't yet"
		subject = static.MIGRATION_MESSAGE_SUBJECT_ONE.format(subreddit=subreddits[0])
	else:
		which, there = "these subreddits", "in them"
		hasnt = "haven't" if all_opted_out else "haven't yet"
		others = len(subreddits) - 1
		subject = static.MIGRATION_MESSAGE_SUBJECT_MANY.format(
			subreddit=subreddits[0],
			others=f"{others} other subreddit{'s' if others > 1 else ''}")

	body = static.MIGRATION_MESSAGE_BODY.format(
		listed=listed,
		which=which,
		hasnt=hasnt,
		there=there,
		install_ask="" if all_opted_out else static.MIGRATION_MESSAGE_INSTALL_ASK.format(link=static.MIGRATION_POST),
		link=static.MIGRATION_POST)
	return subject, body
