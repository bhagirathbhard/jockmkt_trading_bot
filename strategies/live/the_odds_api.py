import requests
import json
import pandas as pd
import os
import numpy as np
from dotenv import load_dotenv

def json_to_dataframe(json_data):
    data = []

    for market in json_data:
        market_key = market["key"]
        last_update = market["last_update"]

        for outcome in market["outcomes"]:
            if outcome["name"] == "Under":  # Skip the "Under" outcomes
                continue

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
    filepath = os.path.join("playerprops", filename)
    dataframe.to_csv(filepath, index=False)
    print(f"Data saved as CSV file '{filepath}'")

def save_to_json(player_odds, filename):
    filepath = os.path.join("playerprops", filename)
    with open(filepath, "w") as json_file:
        json.dump(player_odds, json_file, indent=2)

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

def calculate_projected_fantasy_points(df: pd.DataFrame, event_weights: dict) -> pd.DataFrame:
    
    # Adjust 'Point' column values using np.ceil
    df['AdjustedPoint'] = np.ceil(df['Point'])
    
    # Convert 'Price' to probability using American odds
    df['Probability'] = df['Price'].apply(lambda price: 100 / (100 + price) if price > 0 else -price / (100 - price))
    
    # Add the scores from the event_weights dictionary
    df['Score'] = df['MarketKey'].map(event_weights)
    
    # Compute the row-wise fantasy score points by multiplying AdjustedPoint, Probability, and Score
    df['FantasyScorePoint'] = df['AdjustedPoint'] * df['Probability'] * df['Score']

    # Calculate the mean fantasy score per player for each market key and create a new column with the mean values
    df['MeanFantasyScore'] = df.groupby(['MarketKey', 'Description'])['FantasyScorePoint'].transform('mean')

    # Drop duplicates to keep only unique mean fantasy scores for each player across different market keys
    unique_means = df[['MarketKey', 'Description', 'MeanFantasyScore']].drop_duplicates()

    # Group by 'Description', sum unique mean fantasy scores, and reset index
    summed_means = unique_means.groupby('Description')[['MeanFantasyScore']].sum().reset_index()

    # Merge the summed final projected fantasy score back into the original DataFrame
    df = df.merge(summed_means, on='Description', suffixes=('', '_Sum'))

    # Rename the 'MeanFantasyScore_Sum' column to 'FinalProjectedFPS'
    df.rename(columns={'MeanFantasyScore_Sum': 'FinalProjectedFPS'}, inplace=True)

    # Return the DataFrame with the final projected fantasy score
    return df

def generate_player_projected_fps_summary(csv_filepath: str, output_filename: str) -> None:
    # Create an absolute file path using the current working directory
    abs_csv_filepath = os.path.join(os.getcwd(), "playerprops", csv_filepath)

    # 1. Read the CSV file using Pandas
    df = pd.read_csv(abs_csv_filepath)

    # 2. Process the DataFrame to keep only unique players with their respective FinalProjectedFPS
    players = df[['Description', 'FinalProjectedFPS']].drop_duplicates()

    # 3. Convert the DataFrame into a JSON list of dictionaries
    players_list = players.to_dict(orient='records')

    # 4. Save the final JSON list to a JSON file
    output_filepath = os.path.join("playerprops", output_filename)
    with open(output_filepath, 'w') as json_file:
        json.dump(players_list, json_file, indent=2)

    print(f"Player summary saved as JSON file '{output_filepath}'")

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
            os.makedirs("playerprops", exist_ok=True)
            print("\nPlayer odds for the selected event:")

            filename = f"player_props_{selected_event_id}.json"
            save_to_json(player_odds, filename)
            print(f"\nPlayer props data saved as JSON file '{filename}'")
            
            # Convert JSON to DataFrame
            df = json_to_dataframe(player_odds)
            
            # Calculate projected fantasy score points
            event_weights = {
                'batter_singles': 2.5,
                'batter_doubles': 3,
                'batter_triples': 3.5,
                'batter_home_runs': 4,
                'batter_walks': 2,
                'batter_runs_scored': 2,
                'batter_rbis': 2,
                'batter_stolen_bases': 3,
                'batter_strikeouts': -1
            }
            projected_points_df = calculate_projected_fantasy_points(df, event_weights)
            # Save the dataframe with projected fantasy points to a new CSV        
            fantasy_csv_filename = f"fantasy_points_{selected_event_id}.csv"
            save_to_csv(projected_points_df, fantasy_csv_filename)
            generate_player_projected_fps_summary(fantasy_csv_filename, f"player_fps_summary_{selected_event_id}.json")
        else:
            print(f"No player odds found for the selected event")
    else:
        print("No odds found")