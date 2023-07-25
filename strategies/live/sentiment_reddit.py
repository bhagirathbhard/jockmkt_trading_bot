import csv
import datetime
import os
from typing import List, Tuple

import nltk
import praw
from dotenv import load_dotenv
from nltk.sentiment import SentimentIntensityAnalyzer

nltk.download("vader_lexicon")
load_dotenv()

CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
USER_AGENT = os.environ['USER_AGENT']

reddit = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)

player_names_input = input("Enter the player names separated by commas: ")
player_names = [name.strip() for name in player_names_input.split(',')]
subreddits_input = input("Enter the subreddits separated by commas: ")
subreddits = '+'.join([subreddit.strip() for subreddit in subreddits_input.split(',')])

def get_reddit_posts(player_name: str, subreddit: praw.models.Subreddit, time_filter: str = 'month') -> List[Tuple[str]]:
    posts = []

    query = f"{player_name}"
    for submission in subreddit.search(query, time_filter=time_filter, limit=None, sort='new'):

        submission_comments = list(submission.comments)[:10]
        comments_with_player_name = [comment.body for comment in submission_comments if (player_name.lower() in comment.body.lower())]

        if comments_with_player_name:
            comments = ' '.join(comments_with_player_name)
            posts.append((submission.title, submission.selftext, submission.url, comments))
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

    sentiment_score = 0 if not sentiment_scores else sum(sentiment_scores) / len(sentiment_scores)
    return sentiment_score


def export_to_csv(players_sentiments: List[dict], file_name: str = "players_sentiments.csv"):

    with open(file_name, mode="w") as csv_file:
        fieldnames = ["Player Name", "Sentiment This Week", "Sentiment This Month", "URLs", "Comments"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writeheader()
        for player_sentiment in players_sentiments:
            writer.writerow(player_sentiment)

if __name__ == "__main__":
    players_sentiments = []

    for player_name in player_names:
        subreddit_instance = reddit.subreddit(subreddits)

        posts_this_week = get_reddit_posts(player_name, subreddit_instance, time_filter="week")
        posts_this_month = get_reddit_posts(player_name, subreddit_instance, time_filter="month")

        if not posts_this_week and not posts_this_month:
            print(f"No posts found for {player_name}")
            continue

        sentiment_this_week = sum(sentiment_analysis(post) for post in posts_this_week) / len(posts_this_week) if posts_this_week else 0
        sentiment_this_month = sum(sentiment_analysis(post) for post in posts_this_month) / len(posts_this_month) if posts_this_month else 0

        post_urls = [post[2] for post in posts_this_week + posts_this_month]
        extracted_comments = [post[3] for post in posts_this_week + posts_this_month]

        player_sentiment = {
            "Player Name": player_name,
            "Sentiment This Week": sentiment_this_week,
            "Sentiment This Month": sentiment_this_month,
            "URLs": ','.join(post_urls),
            "Comments": ','.join(extracted_comments)
        }
        players_sentiments.append(player_sentiment)

    export_to_csv(players_sentiments)
    print("CSV file generated successfully.")