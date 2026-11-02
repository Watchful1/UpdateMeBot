import static
import migration_message


def test_single_subreddit():
	subject, body = migration_message.render(["nosleep"])
	assert subject == "Your UpdateMeBot notifications for r/nosleep will stop soon"
	assert body.startswith("Hi! You use UpdateMeBot to get notified about new posts in **r/nosleep**.")
	assert "only work in subreddits where the app is installed. When the switch happens, " \
		"your notifications for posts in r/nosleep will stop." in body
	assert body.endswith(
		f"ask questions on [the announcement post]({static.MIGRATION_POST}). Replies sent to this message aren't read by a person.")


def test_nothing_asks_the_reader_to_act():
	_, body = migration_message.render(["nosleep"])
	for phrase in ("moderator", "install it", "resubscribe"):
		assert phrase not in body.lower()


def test_two_and_three_subreddits_are_listed_in_full():
	subject, body = migration_message.render(["A", "B"])
	assert subject == "Your UpdateMeBot notifications for r/A and 1 other subreddit will stop soon"
	assert "**r/A and r/B**" in body
	assert "your notifications for posts in these subreddits will stop" in body

	subject, body = migration_message.render(["A", "B", "C"])
	assert subject == "Your UpdateMeBot notifications for r/A and 2 other subreddits will stop soon"
	assert "**r/A, r/B and r/C**" in body


def test_long_lists_are_capped():
	subject, body = migration_message.render(["A", "B", "C", "D", "E"])
	assert subject == "Your UpdateMeBot notifications for r/A and 4 other subreddits will stop soon"
	assert "**r/A, r/B, r/C and 2 more**" in body


def test_profiles_read_as_the_authors_profile():
	subject, body = migration_message.render(["u_SomeAuthor"])
	assert subject == "Your UpdateMeBot notifications for u/SomeAuthor's profile will stop soon"
	assert "posts in u/SomeAuthor's profile will stop" in body


def test_subject_fits_reddits_limit_with_the_longest_names():
	subject, _ = migration_message.render(["a" * 21, "b" * 21])
	assert len(subject) <= 100
	subject, _ = migration_message.render(["a" * 21] + ["x"] * 99)
	assert len(subject) <= 100


def test_long_profile_name_is_shortened_in_the_subject_only():
	subreddits = ["u_StreetOrganization54", "Incestconfessions", "LightningStories", "Erotica", "girlscontrolled"]
	subject, body = migration_message.render(subreddits)
	assert subject == "Your UpdateMeBot notifications for u/StreetOrganization54 and 4 other subreddits will stop soon"
	assert "**u/StreetOrganization54's profile, r/Incestconfessions" in body
	subject, _ = migration_message.render(["u_" + "a" * 20] + ["x"] * 99)
	assert len(subject) <= 100
	# Short profile names keep the full wording
	subject, _ = migration_message.render(["u_Bob", "x"])
	assert subject == "Your UpdateMeBot notifications for u/Bob's profile and 1 other subreddit will stop soon"


def test_modmail_with_usage():
	subject, body = migration_message.render_modmail("HFY", 38439, 691915)
	assert subject == "About UpdateMeBot in r/HFY"
	assert body.startswith("Hi r/HFY mods,\n\nI'm u/Watchful1, and I run UpdateMeBot.")
	assert "38,439 people are subscribed to authors in r/HFY, and in the last 90 days the bot sent " \
		"691,915 notifications for posts in your sub." in body
	assert f"the instructions are [here]({static.MIGRATION_POST})" in body
	assert "just reply to this message" in body


def test_modmail_drops_the_usage_clause_below_the_minimum():
	_, body = migration_message.render_modmail("legaladvice", 2100, static.MODMAIL_MIN_NOTIFICATIONS - 1)
	assert "2,100 people are subscribed to authors in r/legaladvice.\n\n" in body
	assert "notifications for posts in your sub" not in body
	assert "once the switch happens, their notifications will stop" in body
	_, body = migration_message.render_modmail("legaladvice", 2100, static.MODMAIL_MIN_NOTIFICATIONS)
	assert "notifications for posts in your sub" in body
