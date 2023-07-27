import requests
import json
import pandas as pd
import os
from dotenv import load_dotenv

def json_to_dataframe(json_data):
    data = []

    for market in json_data:
        market_key = market["key"]
        last_update = market["last_update"]

        for outcome in market["outcomes"]:
            data.append({
                "MarketKey": market_key,
                "LastUpdate": last_update,
                "Name": outcome["name"],
                "Description": outcome["description"],
                "Price": outcome["price"],
                "Point": outcome["point"]
            })

    df = pd.DataFrame(data)
    return df

def save_to_csv(dataframe, filename):
    dataframe.to_csv(filename, index=False)
    print(f"Data saved as CSV file '{filename}'")

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

def get_player_odds(api_key: str, event_id: str):
    market_keys = [
    "batter_home_runs",
    "batter_singles",
    "batter_doubles",
    "batter_triples",
    "batter_runs_batted_in",
    "batter_runs_scored",
    "batter_walks",
    "batter_strikeouts",
    "batter_stolen_bases",
    "batter_rbis"
    ]

    all_player_odds = []

    for market_key in market_keys:
        url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds?apiKey={api_key}&regions=us&markets={market_key}&oddsFormat=american"
        response = requests.get(url)

        if response.status_code == 200:
            player_odds = json.loads(response.text)
            if "bookmakers" in player_odds:
                for bookmaker in player_odds["bookmakers"]:
                    all_player_odds.extend(bookmaker["markets"])
            else:
                print(f"No data found for market {market_key} in the response.")
        else:
            print(f"Error fetching player odds for market {market_key}: {response.status_code}")

    return all_player_odds

def save_to_json(player_odds, filename):
    with open(filename, "w") as json_file:
        json.dump(player_odds, json_file, indent=2)

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

            filename = f"player_props_{selected_event_id}.json"
            save_to_json(player_odds, filename)
            print(f"\nPlayer props data saved as JSON file '{filename}'")
            # Convert JSON to DataFrame
            df = json_to_dataframe(player_odds)
            # Save the DataFrame to CSV
            csv_filename = f"player_props_{selected_event_id}.csv"
            save_to_csv(df, csv_filename)
        else:
            print(f"No player odds found for the selected event")

    else:
        print("No odds found")