#!/usr/bin/env python

# This is the Reddit Analysis project.
#
# Copyright 2013 Randal S. Olson.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/.

import csv
import praw
import string
import sys
from collections import defaultdict
from optparse import OptionParser
from requests.exceptions import HTTPError

popular_words = defaultdict(int)
common_words = set()

# punctuation to strip from words
PUNCTUATION = " " + string.punctuation + "\n"

# load a list of common words to ignore
with open("common-words.csv", "r") as common_words_file:
    for common_word_file_line in csv.reader(common_words_file):
        for common_word in common_word_file_line:
            common_words.add(common_word.strip(PUNCTUATION).lower())

with open("/usr/share/dict/words", "r") as dictionary_file:
    for dictionary_word in dictionary_file:
        common_words.add(dictionary_word.strip(PUNCTUATION).lower())

# put words here that you don't want to include in the word cloud
EXCLUDED_WORDS = ["/", "--", "...", "deleted", ")x"]

# Global Variable Initialization
options = None


def parse_cmd_line():
    # command-line argument parsing
    usage = ("usage: %prog [options] USERNAME TARGET\n\n"
             "USERNAME sets your Reddit username for the bot\n"
             "TARGET sets the subreddit or user to count word frequencies for."
             "\nenter /r/TARGET for subreddits or /u/TARGET for users.")
    parser = OptionParser(usage=usage)

    parser.add_option("-p", "--period",
                      action="store",
                      type="string",
                      dest="period",
                      default="month",
                      help=("period to count words over: "
                            "day/week/month/year/all. [default: month]"))

    parser.add_option("-l", "--limit",
                      action="store",
                      type="int",
                      dest="limit",
                      help=("maximum number of submissions/comments to count "
                            "word frequencies for. When omitted fetch all."))

    parser.add_option("-m", "--maxthresh",
                      action="store",
                      type="float",
                      dest="max_threshold",
                      default=0.34,
                      help=("maximum relative frequency in the text a word can"
                            " appear to be considered in word counts. prevents"
                            " word spamming in a single submission. "
                            "[default: 0.34]"))

    parser.add_option("-o", "--only_one",
                      action="store_false",
                      dest="count_word_freqs",
                      default=True,
                      help=("only count a word once per text block (title, "
                            "selftext, comment body) rather than incrementing"
                            "the total for for each instance."))

    global options
    options, args = parser.parse_args()

    if len(args) != 2:
        parser.error("Invalid number of arguments provided.")
    user, target = args

    if target.startswith("/r/"):
        options.is_subreddit = True
    elif target.startswith("/u/"):
        options.is_subreddit = False
    else:
        parser.error("Invalid target.")

    if options.period not in ["day", "week", "month", "year", "all"]:
        parser.error("Invalid period.")

    return user, target


def parse_text(text):
    """Parse the passed in text and add words that are not common."""
    total = 0.0  # intentionally a float
    text_words = defaultdict(int)
    for word in text.split():  # Split on all whitespace
        word = word.strip(PUNCTUATION).lower()
        total += 1
        if word and word not in common_words:
            text_words[word] += 1

    # Add to popular_words list
    for word, count in text_words.items():
        if count / total <= options.max_threshold:
            if options.count_word_freqs:
                popular_words[word] += count
            else:
                popular_words[word] += 1


def process_redditor(redditor):
    """Parse submissions and comments for the given Redditor."""
    for entry in with_status(redditor.get_overview(limit=options.limit)):
        if isinstance(entry, praw.objects.Comment):  # Parse comment
            parse_text(entry.body)
        else:  # Parse submission
            process_submission(entry, include_comments=False)


def process_submission(submission, include_comments=True):
    """Parse a submission's text and body (if applicable).

    Include the submission's comments when `include_comments` is True.

    """
    if include_comments:  # parse all the comments for the submission
        submission.replace_more_comments()
        for comment in praw.helpers.flatten_tree(submission.comments):
            parse_text(comment.body)

    # parse the title of the submission
    parse_text(submission.title)

    # parse the selftext of the submission (if applicable)
    if submission.is_self:
        parse_text(submission.selftext)


def process_subreddit(subreddit):
    """Parse comments, title text, and selftext in a given subreddit."""

    # determine period to count the words over
    params = {'t': options.period}
    for submission in with_status(subreddit.get_top(limit=options.limit,
                                                    params=params)):
        try:
            process_submission(submission)
        except HTTPError as exc:
            sys.stderr.write("\nSkipping submission {0} due to HTTP status {1}"
                             " error. Continuing...\n"
                             .format(submission.url, exc.response.status_code))
            continue


def with_status(iterable):
    """Wrap an iterable outputting '.' for each item (up to 50 a line)."""
    for i, item in enumerate(iterable):
        sys.stderr.write('.')
        sys.stderr.flush()
        if i % 100 == 99:
            sys.stderr.write('\n')
        yield item


def main():
    user, target = parse_cmd_line()

    # open connection to Reddit
    r = praw.Reddit(user_agent="bot by /u/{0}".format(user))
    r.config.decode_html_entities = True

    # run analysis
    sys.stderr.write("Analyzing {0}\n".format(target))
    sys.stderr.flush()

    target = target[3:]

    if options.is_subreddit:
        process_subreddit(r.get_subreddit(target))
    else:
        process_redditor(r.get_redditor(target))

    # build a string containing all the words for the word cloud software
    output = ""

    # open output file to store the output string
    out_file_name = target + ".csv"

    if not options.is_subreddit:
            out_file_name = "user-" + out_file_name

    out_file = open(out_file_name, "w")

    for word in sorted(popular_words.keys()):

        # tweak this number depending on the subreddit
        # some subreddits end up having TONS of words and it seems to overflow
        # the Python string buffer
        if popular_words[word] > 2:
            pri = True

            # do not print a word if it is in the excluded word list
            for ew in EXCLUDED_WORDS:
                if ew in word:
                    pri = False
                    break

            # don't print the word if it's just a number
            try:
                int(word)
                pri = False
            except:
                pass

            # add as many copies of the word as it was mentioned in the
            # subreddit
            if pri:
                txt = ((word + " ") * popular_words[word])
                txt = txt.encode("UTF-8").strip(" ")
                txt += " "
                output += txt
                out_file.write(txt)

    out_file.close()

    # print the series of words for the word cloud software
    # place this text into wordle.net
    print output


if __name__ == '__main__':
    sys.exit(main())
