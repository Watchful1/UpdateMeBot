import static
import migration_message


def test_single_subreddit():
	subject, body = migration_message.render(["nosleep"], set())
	assert subject == "Your UpdateMeBot notifications for r/nosleep will stop soon"
	assert "new posts in **r/nosleep**." in body
	assert "and r/nosleep hasn't yet. When the switch happens, your notifications for posts there will stop." in body
	assert f"Moderators can install it from [here]({static.MIGRATION_POST})." in body
	assert body.endswith(f"Comment on the [announcement post]({static.MIGRATION_POST}).")


def test_two_and_three_subreddits_are_listed_in_full():
	subject, body = migration_message.render(["A", "B"], set())
	assert subject == "Your UpdateMeBot notifications for r/A and 1 other subreddit will stop soon"
	assert "**r/A and r/B**" in body
	assert "these subreddits haven't yet" in body
	assert "notifications for posts in them will stop" in body

	subject, body = migration_message.render(["A", "B", "C"], set())
	assert subject == "Your UpdateMeBot notifications for r/A and 2 other subreddits will stop soon"
	assert "**r/A, r/B and r/C**" in body


def test_long_lists_are_capped():
	subject, body = migration_message.render(["A", "B", "C", "D", "E"], set())
	assert subject == "Your UpdateMeBot notifications for r/A and 4 other subreddits will stop soon"
	assert "**r/A, r/B, r/C and 2 more**" in body


def test_all_opted_out_drops_yet_and_the_install_ask():
	subject, body = migration_message.render(["Quiet"], {"quiet"})
	assert "r/Quiet hasn't. When" in body
	assert "Moderators can install it" not in body

	subject, body = migration_message.render(["Quiet", "Other"], {"quiet", "other"})
	assert "these subreddits haven't. When" in body
	assert "Moderators can install it" not in body


def test_partly_opted_out_keeps_the_install_ask():
	subject, body = migration_message.render(["Quiet", "Open"], {"quiet"})
	assert "these subreddits haven't yet" in body
	assert "Moderators can install it" in body


def test_subject_fits_reddits_limit_with_the_longest_names():
	subject, _ = migration_message.render(["a" * 21, "b" * 21], set())
	assert len(subject) <= 100
