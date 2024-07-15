# from flask import Flask, request, jsonify, render_template
# from valorant_stats import get_player_stats, calculate_team_stats, compare_teams
#
# app = Flask(__name__)
#
# @app.route('/')
# def index():
#     return render_template('index.html')
#
# @app.route('/fetch-stats', methods=['POST'])
# def fetch_stats():
#     data = request.json
#     team1_player_ids = data['team1Players']
#     team2_player_ids = data['team2Players']
#
#     team1_stats = [get_player_stats(player_id) for player_id in team1_player_ids]
#     team2_stats = [get_player_stats(player_id) for player_id in team2_player_ids]
#
#     team1_aggregated = calculate_team_stats(team1_stats)
#     team2_aggregated = calculate_team_stats(team2_stats)
#
#     prediction = compare_teams(team1_aggregated, team2_aggregated)
#
#     return jsonify({
#         'team1Stats': team1_stats,
#         'team2Stats': team2_stats,
#         'prediction': prediction
#     })
#
# if __name__ == '__main__':
#     app.run(debug=True)

import logging
from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup
from urllib.parse import quote

app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')
# Configure logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Temporary storage for player stats
player_stats_cache = {
    'team1': {},
    'team2': {}
}

# Function to get player stats
def get_player_stats(player_id):
    logging.debug(f"Fetching stats for player ID: {player_id}")
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    encoded_player_id = quote(player_id)
    url = f'https://tracker.gg/valorant/profile/riot/{encoded_player_id}/overview'
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    data = soup.find_all('div', class_='stat')
    stats = {}
    for item in data:
        try:
            stat_name = item.find('span', class_='name').get_text().strip()
            stat_value = item.find('span', class_='value').get_text().strip()
            stats[stat_name] = stat_value
        except AttributeError:
            continue
    driver.quit()
    logging.debug(f"Stats fetched for player ID: {player_id} - {stats}")
    return stats

def calculate_team_stats(team_stats):
    def average(lst):
        return sum(lst) / len(lst) if lst else 0

    logging.debug(f"Calculating team stats for: {team_stats}")

    team_aggregated = {
        "RR": average([float(player.get("RR", 0)) for player in team_stats]),
        "Level": average([float(player.get("Level", 0)) for player in team_stats]),
        "D/R": average([float(player.get("Damage/Round", 0)) for player in team_stats]),
        "K/D": average([float(player.get("K/D Ratio", 0)) for player in team_stats]),
        "HS%": average([float(str(player.get("Headshot %", 0)).strip('%')) for player in team_stats]),
        "Win%": average([float(str(player.get("Win %", 0)).strip('%')) for player in team_stats]),
        "Wins": sum([int(str(player.get("Wins", 0)).replace(',', '')) for player in team_stats]),
        "Kills": sum([int(str(player.get("Kills", 0)).replace(',', '')) for player in team_stats]),
        "Deaths": sum([int(str(player.get("Deaths", 0)).replace(',', '')) for player in team_stats]),
        "Assists": sum([int(str(player.get("Assists", 0)).replace(',', '')) for player in team_stats]),
        "KAST": average([float(str(player.get("KAST", 0)).strip('%')) for player in team_stats]),
        "DDΔ/R": average([float(player.get("DDΔ/Round", 0)) for player in team_stats]),
        "ACS": average([float(player.get("ACS", 0)) for player in team_stats]),
        "KAD": average([float(player.get("KAD Ratio", 0)) for player in team_stats]),
    }
    logging.debug(f"Team aggregated stats: {team_aggregated}")
    return team_aggregated

def compare_teams(team1_score, team2_score):
    logging.debug(f"Comparing teams - Team 1 Score: {team1_score}, Team 2 Score: {team2_score}")
    if team1_score > team2_score:
        return "Team 1 is more likely to win."
    elif team2_score > team1_score:
        return "Team 2 is more likely to win."
    else:
        return "The teams are evenly matched."

@app.route('/fetch-player-stats', methods=['POST'])
def fetch_player_stats():
    data = request.json
    player_id = data.get('playerId')
    team = data.get('team')

    logging.debug(f"Received request to fetch player stats - Player ID: {player_id}, Team: {team}")

    try:
        player_stats = get_player_stats(player_id)
        player_stats_cache[team][player_id] = player_stats
        logging.debug(f"Player stats cached - {team}: {player_stats_cache[team]}")
        return jsonify(player_stats)
    except Exception as e:
        logging.error(f"Error fetching player stats for {player_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/calculate-results', methods=['POST'])
def calculate_results():
    logging.debug("Received request to calculate results")

    try:
        team1_stats = list(player_stats_cache['team1'].values())
        team2_stats = list(player_stats_cache['team2'].values())

        logging.debug(f"Team 1 stats: {team1_stats}")
        logging.debug(f"Team 2 stats: {team2_stats}")

        team1_aggregated = calculate_team_stats(team1_stats)
        team2_aggregated = calculate_team_stats(team2_stats)

        stat_weights = {
            "RR": 1,
            "Level": 1,
            "D/R": 2,
            "K/D": 3,
            "HS%": 1,
            "Win%": 3,
            "Wins": 1,
            "Kills": 2,
            "Deaths": 1,
            "Assists": 1,
            "KAST": 2,
            "DDΔ/R": 1,
            "ACS": 2,
            "KAD": 2
        }

        def calculate_weighted_score(team_stats):
            weighted_score = 0
            for stat, weight in stat_weights.items():
                weighted_score += team_stats[stat] * weight
            return weighted_score

        team1_score = calculate_weighted_score(team1_aggregated)
        team2_score = calculate_weighted_score(team2_aggregated)

        prediction = compare_teams(team1_score, team2_score)

        logging.debug(f"Prediction: {prediction}")

        return jsonify({
            'team1Stats': team1_aggregated,
            'team2Stats': team2_aggregated,
            'prediction': prediction
        })
    except Exception as e:
        logging.error(f"Error calculating results: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
