import sys
import unittest
import word_freqs as wf
import praw
from collections import defaultdict


class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.user, self.target = wf.parse_cmd_line()
        wf.popular_words = defaultdict(int)

    def test_parse_cmd_line(self):
        self.user, self.target = wf.parse_cmd_line()
        self.assertEqual(self.user, sys.argv[1])
        self.assertEqual(self.target, sys.argv[2])

    def test_parse_text(self):
        popular_words = defaultdict(int)

        popular_words["testggg"] = 4
        popular_words["gggtestggg"] = 4
        popular_words["gytestyg"] = 3
        popular_words["ygtestgy"] = 5

        txt = ""
        for word, freq in popular_words.items():
            txt += str((word + " ") * freq)

        wf.parse_text(txt)
        self.assertEqual(popular_words, wf.popular_words)

        # TODO: still need to test:
        # anti-spamming w/ max_threshold
        # count word freqs vs only count one word per sentence

    def test_process_redditor(self):
        """
        Can't think of an easy, repeatable way to test this right now.

        TODO: make our own test redditor
        """

    def test_process_submission(self):
        # open connection to Reddit
        r = praw.Reddit(user_agent="test bot by test")
        r.config.decode_html_entities = True

        popular_words = {
            "reddit": 48,
            "upvoted": 32,
            "upvote": 23,
            "comments": 13,
            "3": 12,
            "fuck": 11,
            "qgyh2": 9,
            "upvotes": 9,
            "fucking": 8,
            "posts": 7
        }
        wfpw = defaultdict(int)

        # parse a fixed thread
        # TODO: make our own test thread
        sub = r.get_submission(url="http://www.reddit.com/r/pics/comments/92dd8/test_post_please_ignore/")
        wf.process_submission(sub)

        # only look at the top 10 most-used words in the thread
        # TODO: look at all words used in thread
        ct = 0
        for key in sorted(wf.popular_words, key=wf.popular_words.get, reverse=True):
            wfpw[key] = wf.popular_words[key]
            ct += 1
            if ct >= 10:
                break

        self.assertEqual(popular_words, wfpw)

    def test_process_subreddit(self):
        """
        Can't think of an easy, repeatable way to do this right now.

        TODO: make our own test subreddit
        """

    def test_with_status(self):
        """
        Is this even a function that should be tested?
        """

if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
