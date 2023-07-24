import requests
import json
import csv
import pandas as pd
import os
from dotenv import load_dotenv

def get_sport_odds(api_key: str, sport: str):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds?regions=us&apiKey={api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        odds = json.loads(response.text)
        print(odds)
        return odds
    else:
        print(f"Error fetching odds: {response.status_code}")
        return None

''''def filter_sport_odds(odds, game_date):
    date_pattern = re.compile(rf"{game_date}")

    filtered_odds = [
        event
        for event in odds
        if "commence_time" in event
        and date_pattern.match(event["commence_time"])
        and "teams" in event.get("markets", [{}])[0]
    ]
    return filtered_odds
'''

def get_player_odds(api_key: str, event_id: str):
    market_keys = [
        "batter_home_runs",
        "batter_hits",
        "batter_total_bases",
        "batter_rbis",
        "batter_runs_scored",
        "batter_hits_runs_rbis",
        "batter_singles",
        "batter_doubles",
        "batter_triples",
        "batter_walks",
        "batter_strikeouts",
        "batter_stolen_bases",
        "pitcher_strikeouts",
        "pitcher_record_a_win",
        "pitcher_hits_allowed",
        "pitcher_walks",
        "pitcher_earned_runs",
        "pitcher_outs",
    ]

    all_player_odds = []

    for market_key in market_keys:
        url = f"https://api.the-odds-api.com/v4/events/{event_id}/odds?regions=us&markets={market_key}&apiKey={api_key}"
        response = requests.get(url)

        if response.status_code == 200:
            player_odds = json.loads(response.text)
            all_player_odds.extend(player_odds)
        else:
            print(f"Error fetching player odds for market {market_key}: {response.status_code}")

    # Merge API responses using pandas
    if all_player_odds:
        odds_df = pd.DataFrame(all_player_odds)
        odds_df = odds_df.groupby("name").agg({"outcomes": "sum"}).reset_index()
        merged_player_odds = odds_df.to_dict("records")
    else:
        print("No player props data is available for the selected event.")
        merged_player_odds = None

    return merged_player_odds

def export_to_csv(player_odds, filename):
    with open(filename, "w", newline="") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Player Name", "Over/Under Odds"])

        for odds in player_odds:
            player_name = odds["name"]
            player_odds_list = []

            for outcome in odds["outcomes"]:
                odds_str = f"{outcome['type']} {outcome['points']} ({outcome['price']})"
                player_odds_list.append(odds_str)

            csv_writer.writerow([player_name] + player_odds_list)


if __name__ == "__main__":
    load_dotenv()
    api_key = os.environ.get("ODDS_API_KEY")
    sport = "baseball_mlb"
    odds = get_sport_odds(api_key, sport)

    if odds:
        print(f"Upcoming games for {sport}:")
        for event in odds:
            print(f"Event ID: {event['id']}, Teams: {event['home_team']} vs {event['away_team']}, Commence Time: {event['commence_time']}")

        selected_event_id = input("\nEnter the event ID to fetch player props: ")

        player_odds = get_player_odds(api_key, selected_event_id)

        if player_odds:
            print("\nPlayer odds for the selected event:")
            print(json.dumps(player_odds, indent=2))

            filename = f"player_props_{selected_event_id}.csv"
            export_to_csv(player_odds, filename)
            print(f"\nPlayer props data exported to CSV file '{filename}'")
        else:
            print(f"No player odds found for the selected event")

    else:
        print("No odds found")