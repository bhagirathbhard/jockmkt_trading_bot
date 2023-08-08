import csv
import datetime
import glob
import json
import os
from typing import List, Tuple

import nltk
import praw.models
from dotenv import load_dotenv
from nltk.sentiment import SentimentIntensityAnalyzer

nltk.download("vader_lexicon")


def get_reddit_posts(player_names: List[str], reddit: praw.Reddit, subreddit_names: List[str], num_posts: int = 5, num_comments: int = 10) -> List[Tuple[str]]:
    posts = []
    print(player_names)
    for subreddit_name in subreddit_names:
        subreddit_instance = reddit.subreddit(subreddit_name)
        hot_posts = subreddit_instance.hot(limit=num_posts)

        for submission in hot_posts:
            submission_comments = []
            submission.comments.replace_more(limit=0)  # Remove "MoreComments" instances
            for comment in submission.comments.list()[:num_comments]:
                # Check if any player name variation is present in the comment
                if any(name.lower() in comment.body.lower() for name in player_names):
                    submission_comments.append(comment.body)

            if submission_comments:
                comments = " ".join(submission_comments)
                posts.append((submission.title, submission.selftext, submission.url, comments))
    print(posts)
    return posts


def sentiment_analysis(post_tuple: Tuple[str]) -> float:
    sentiment_analyzer = SentimentIntensityAnalyzer()
    sentiment_scores = []

    sentiment_title = sentiment_analyzer.polarity_scores(post_tuple[0])
    sentiment_scores.append(sentiment_title["compound"])

    sentiment_selftext = sentiment_analyzer.polarity_scores(post_tuple[1])
    sentiment_scores.append(sentiment_selftext["compound"])

    comments = post_tuple[-1]
    sentiment_comments = sentiment_analyzer.polarity_scores(comments)
    sentiment_scores.append(sentiment_comments["compound"])

    sentiment_score = (
        0 if not sentiment_scores else sum(sentiment_scores) / len(sentiment_scores)
    )
    return sentiment_score

def main():
    # Load environment variables and configure Reddit API
    load_dotenv()
    CLIENT_ID = os.environ["CLIENT_ID"]
    CLIENT_SECRET = os.environ["CLIENT_SECRET"]
    USER_AGENT = os.environ["USER_AGENT"]
    reddit = praw.Reddit(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT
    )

    # Get subreddits_input
    subreddits_input = input("Enter the subreddits separated by commas: ")
    subreddits = [subreddit.strip() for subreddit in subreddits_input.split(',')]

    # List all JSON files in the playerprops folder
    json_files = glob.glob("/Users/bhagirathbhardwaj/Documents/GitHub/jockmkt_trading_bot/strategies/live/playerprops/*.json")

    # Iterate through each JSON file
    for json_file_path in json_files:
        # Read JSON data from the file and save it to a Python variable
        with open(json_file_path, "r") as json_file:
            json_data = json.load(json_file)

        # Perform sentiment analysis for each player's name in the JSON data
        players_sentiments = []
        for player in json_data:
            player_name = player["Description"]
            variations = [player_name, player_name.split(" ")[0], player_name.split(" ")[-1]]
            posts_from_given_subs = get_reddit_posts(variations, reddit, subreddits)
            sentiment_this_month = (
                sum(sentiment_analysis(post) for post in posts_from_given_subs)
                / len(posts_from_given_subs)
                if posts_from_given_subs
                else 0
            )

            player_sentiment = {
                "Player Name": player_name,
                "Sentiment This Month": sentiment_this_month,
            }
            players_sentiments.append(player_sentiment)

        # Update the JSON data with sentiment scores
        for player in json_data:
            player_name = player["Description"]
            sentiment_found = False

            for player_sentiment in players_sentiments:
                if player_sentiment["Player Name"] == player_name:
                    sentiment_month_score = player_sentiment["Sentiment This Month"]
                    player["Sentiment Score"] = (
                        sentiment_month_score if sentiment_month_score != "NA" else 0
                    )
                    sentiment_found = True
                    break

            if not sentiment_found:
                player["Sentiment Score"] = 0

        # Save updated JSON data to a new JSON file
        json_output_file_path = json_file_path.replace(".json", "_with_sentiment.json")
        with open(json_output_file_path, "w") as json_file:
            json.dump(json_data, json_file, indent=2)


if __name__ == "__main__":
    main()