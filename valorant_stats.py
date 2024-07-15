from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
import concurrent.futures
import time
from bs4 import BeautifulSoup
from urllib.parse import quote
import pandas as pd

app = Flask(__name__)

# Function to get player stats
def get_player_stats(player_id):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
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
    return stats

def calculate_team_stats(team_stats):
    def average(lst):
        return sum(lst) / len(lst) if lst else 0

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
    return team_aggregated


def compare_teams(team1_score, team2_score):
    if team1_score > team2_score:
        return "Team 1 is more likely to win."
    elif team2_score > team1_score:
        return "Team 2 is more likely to win."
    else:
        return "The teams are evenly matched."

@app.route('/fetch-stats', methods=['POST'])
def fetch_stats():
    data = request.json
    team1_players = data.get('team1Players')
    team2_players = data.get('team2Players')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        team1_stats = list(executor.map(get_player_stats, team1_players))
        team2_stats = list(executor.map(get_player_stats, team2_players))

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

    return jsonify({
        'team1Stats': team1_aggregated,
        'team2Stats': team2_aggregated,
        'prediction': prediction
    })

if __name__ == '__main__':
    app.run(debug=True)
