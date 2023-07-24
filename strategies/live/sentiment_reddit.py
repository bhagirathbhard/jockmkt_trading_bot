import nltk
import praw
import csv
import os
import datetime
from typing import List, Tuple
from nltk.sentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

nltk.download("vader_lexicon")

load_dotenv()
# set your keys here or in your system environment variables
CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']
USER_AGENT = os.environ['USER_AGENT']

# Set up Reddit API
reddit = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)

def get_reddit_posts(player_name: str, count: int = 100, days: int = 14) -> List[Tuple[str]]:
    posts = []
    try:
        query = f"{player_name} timestamp:{int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())}"
        for submission in reddit.subreddit("soccer").search(query, time_filter="month", limit=count, sort='relevance'):
            # Get up to the first 10 top-level comments
            submission_comments = list(submission.comments)[:10]
            comments = ' '.join([comment.body for comment in submission_comments if not hasattr(comment, "body")])
            posts.append((submission.title, submission.selftext, submission.url, comments))
    except Exception as e:
        print(f"Error fetching Reddit posts: {e}")
    return posts

def sentiment_analysis(post_tuple: Tuple[str]) -> float:
    sentiment_analyzer = SentimentIntensityAnalyzer()
    sentiment_scores = []

    # Post title
    sentiment_title = sentiment_analyzer.polarity_scores(post_tuple[0])
    sentiment_scores.append(sentiment_title["compound"])

    # Self-text
    sentiment_selftext = sentiment_analyzer.polarity_scores(post_tuple[1])
    sentiment_scores.append(sentiment_selftext["compound"])

    # Comments
    comments = post_tuple[-1]
    sentiment_comments = sentiment_analyzer.polarity_scores(comments)
    sentiment_scores.append(sentiment_comments["compound"])

    sentiment_score = 0 if not sentiment_scores else sum(sentiment_scores) / len(sentiment_scores)
    return sentiment_score

def export_to_csv(players_sentiments: List[dict], file_name: str = "players_sentiments.csv"):

    with open(file_name, mode="w") as csv_file:
        fieldnames = ["Player Name", "Sentiment Score", "URLs"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        writer.writeheader()
        for player_sentiment in players_sentiments:
            writer.writerow(player_sentiment)

if __name__ == "__main__":
    player_names = ["Declan Rice", "Mason Greenwood", "Harry Kane", "Marcus Rashford"]
    players_sentiments = []

    for player_name in player_names:
        posts = get_reddit_posts(player_name)

        if not posts:
            print(f"No posts found for {player_name}")
            continue

        player_sentiment_sum = 0
        post_urls = []
        for post in posts:
            sentiment_score = sentiment_analysis(post)
            player_sentiment_sum += sentiment_score
            post_urls.append(post[2])
            
        average_sentiment = player_sentiment_sum / len(posts)

        player_sentiment = {
            "Player Name": player_name,
            "Sentiment Score": average_sentiment,
            "URLs": ','.join(post_urls)  # Comma-separated list of all Reddit post URLs
        }
        players_sentiments.append(player_sentiment)

    export_to_csv(players_sentiments)
    print("CSV file generated successfully.")