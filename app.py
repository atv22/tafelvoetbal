import time
import datetime
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import numpy as np

Versie = "Beta versie 0.3.0 - 16 september 2023"

st.set_page_config(page_title="Tafelvoetbal", page_icon="⚽", layout="centered", initial_sidebar_state="auto",
                   menu_items=None)

# CSS to inject contained in a string
hide_dataframe_row_index = """
            <style>
            .row_heading.level0 {display:none}
            .blank {display:none}
            </style>
            """

# Inject CSS with Markdown
st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)


# Define a function to add a name to the Google Sheet
def add_name(name):
    """
    Add a name to the Google Sheet if it meets certain criteria.

    Args:
        name (str): The name to be added.

    Returns:
        None
    """
    # Check if the name contains only alphabetic characters
    if not name.isalpha():
        st.error("De naam mag alleen letters bevatten. Verander de naam naar alleen letters.")
    # Check if the length of the name is between 2 and 50 characters
    elif len(name) < 2 or len(name) > 50:
        st.error("De lengte van de naam moet tussen de 2 en de 50 tekens zijn. Pas de lengte van de naam aan.")
    # Check if the first letter of the name is uppercase
    elif not name[0].isupper():
        st.error("De eerste letter van de naam moet een hoofdletter zijn.")
    else:
        # Check if the name already exists
        existing_names_sheet = client.open('Tafelvoetbal').worksheet("Namen")
        existing_names = existing_names_sheet.col_values(1)[1:]
        if name in existing_names:
            st.error("Naam bestaat al! Vul een andere naam in.")
        else:
            new_row = [name]
            # Add the new name to the Google Sheet
            existing_names_sheet.append_row(new_row)
            st.success(f"Naam '{name}' toegevoegd.")
            time.sleep(2)
            # Rerun the Streamlit app to refresh the state
            st.experimental_rerun()


def get_download_filename(filename, extension):
    """
    Generate a download filename by combining the original filename,
    current date and time, and the provided file extension.

    Args:
        filename (str): The original filename or base name.
        extension (str): The file extension to be appended.

    Returns:
        str: The generated download filename.
    """
    # Format the filename using the original filename, current date and time,
    # and the provided file extension
    return "{0}_{1}.{2}".format(filename,
                                datetime.datetime.now().strftime("%d/%m/%Y_%H%M%S"),
                                extension)


def add_request(request):
    """
    Add a request to the Google Sheet

    Args:
        request (str): The request to be added.

    Returns:
        None
    """

    # Check if the length of the reqeust is between 2 and 250 characters
    if len(request) < 2 or len(request) > 250:
        st.error("De lengte van het verzoek moet tussen de 2 en de 250 tekens zijn. Pas de lengte van het verzoek aan.")
    else:
        # Check if the name already exists
        existing_requests_sheet = client.open('Tafelvoetbal').worksheet("Verzoeken")
        existing_requests = existing_requests_sheet.col_values(1)[1:]
        if request in existing_requests:
            st.error("Verzoek bestaat al! Vul een andere verzoek in.")
        else:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = [request, timestamp]
            # Add the new name to the Google Sheet
            existing_requests_sheet.append_row(new_row)
            st.success(f"Verzoek is toegevoegd.")
            time.sleep(2)
            # Rerun the Streamlit app to refresh the state
            st.experimental_rerun()


# Calculate expected result using the Elo formula
def calculate_expected_result(ta, tb):
    return 1 / (1 + 10 ** ((tb - ta) / 400))


# Calculate new ratings after a match
def calculate_new_rating(rating, k_factor, s, expected_result, score_factor):
    return rating + k_factor * (s - expected_result) * score_factor


# Calculate score factor based on score difference
def calculate_score_factor(score_a, score_b):
    return (score_a - score_b) / abs(score_a - score_b) if score_a != score_b else 0


# Define a function to calculate and update ELO ratings
def calculate_elo_ratings(selected_names, player_ratings, home_score, away_score):
    """
    Calculate ELO ratings for the players in the given match.

    Args:
        selected_names (dict): Dictionary containing selected player names and klinkers.
        player_ratings (pd.DataFrame): DataFrame containing player ELO ratings.
        home_score (int): Score of the home team.
        away_score (int): Score of the away team.

    Returns:
        tuple: Tuple containing ELO changes for home team and away team players.
    """
    # Calculate team totals
    ta = sum(player_ratings.loc[player_ratings['Player'] == player, 'Rating'].values[0] for player in
             selected_names['Thuis'].values())
    tb = sum(player_ratings.loc[player_ratings['Player'] == player, 'Rating'].values[0] for player in
             selected_names['Uit'].values())

    # Calculate expected results
    expected_result_a = calculate_expected_result(ta, tb)
    expected_result_b = calculate_expected_result(tb, ta)

    # Calculate actual results and score factor
    score_factor = calculate_score_factor(home_score + away_score, 20 - (home_score + away_score))
    s = 1 if home_score > away_score else 0

    # Calculate and update ELO ratings for Team A (Thuis)
    for player_key in ['Thuis speler 1', 'Thuis speler 2']:
        player_name = selected_names[player_key]['name']
        idx = player_ratings.index[player_ratings['Player'] == player_name][0]
        expected_result = expected_result_a
        if math.isnan(player_ratings.loc[idx, 'Rating']):
            player_ratings.loc[idx, 'Rating'] = 1000  # Initialize with 1000 if no rating
        new_rating = calculate_new_rating(player_ratings.loc[idx, 'Rating'], K_FACTOR, s, expected_result, score_factor)
        player_ratings.loc[idx, 'Rating'] = new_rating

    # Calculate and update ELO ratings for Team B (Uit)
    for player_key in ['Uit speler 1', 'Uit speler 2']:
        player_name = selected_names[player_key]['name']
        idx = player_ratings.index[player_ratings['Player'] == player_name][0]
        expected_result = expected_result_b
        if math.isnan(player_ratings.loc[idx, 'Rating']):
            player_ratings.loc[idx, 'Rating'] = 1000  # Initialize with 1000 if no rating
        new_rating = calculate_new_rating(player_ratings.loc[idx, 'Rating'], K_FACTOR, 1 - s, expected_result,
                                          score_factor)
        player_ratings.loc[idx, 'Rating'] = new_rating


scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

skey = st.secrets["gcp_service_account"]
credentials = Credentials.from_service_account_info(
    skey,
    scopes=scopes,
)
client = gspread.authorize(credentials)

Uitslag = client.open('Tafelvoetbal').worksheet('Uitslag')
complete_list_of_players = client.open('Tafelvoetbal').worksheet("Namen").col_values(1)[1:]
data = Uitslag.get_all_values()

# Define the Streamlit app
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Invullen", "Ranglijst", "Spelers", "ELO",
                                                    "Ruwe data", "Verzoeken", "Colofon"])

# Tabblad 1 #

with tab1:
    st.title("Tafelvoetbal Competitie ⚽")
    st.header(Versie)
    st.write("Vul de resultaten in:")
    klink = st.radio("Zijn er klinkers gescoord? (Als ja, draai dan je scherm op 📱)", ("Nee", "Ja"))
    # Define dictionary to keep track of selected names and klinkers
    selected_names = {
        'Thuis speler 1': {'name': None, 'klinkers': None},
        'Thuis speler 2': {'name': None, 'klinkers': None},
        'Uit speler 1': {'name': None, 'klinkers': None},
        'Uit speler 2': {'name': None, 'klinkers': None}
    }

    with st.form("formulier"):
        if klink == "Ja":
            c1, c2 = st.columns([2, 1])
        players = sorted(complete_list_of_players)

        # Create dropdowns and number inputs for each player
        if klink == "Ja":
            for title in selected_names:
                with c1:
                    selected_name = st.selectbox(title, players)
                with c2:
                    selected_klinkers = st.number_input(f"Aantal klinkers {title}:", min_value=0, max_value=10, step=1)
                selected_names[title] = {'name': selected_name, 'klinkers': selected_klinkers}
        else:
            for title in selected_names:
                selected_name = st.selectbox(title, players)
                selected_names[title] = {'name': selected_name, 'klinkers': 0}
        # Get the scores from the user
        home_score = st.number_input("Score Thuis team:", min_value=0, max_value=10, step=1)
        away_score = st.number_input("Score Uit team:", min_value=0, max_value=10, step=1)

        # Define the submit button
        if st.form_submit_button("Verstuur"):
            # Check if all required fields are filled in
            if home_score == 10 and away_score == 10:
                st.error('Wijzig de einduitslag. Beide scores kunnen niet 10 zijn.')
            elif home_score != 10 and away_score != 10:
                st.error('Wijzig de einduitslag. Eén van de scores moet 10 zijn.')
            elif len(set(player['name'] for player in selected_names.values())) < len(selected_names):
                st.error("Selecteer elke speler slechts één keer.")
            else:
                time.sleep(1)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                values = [
                    selected_names['Thuis speler 1']['name'],
                    selected_names['Thuis speler 2']['name'],
                    selected_names['Uit speler 1']['name'],
                    selected_names['Uit speler 2']['name'],
                    home_score,
                    away_score,
                    timestamp,
                    selected_names['Thuis speler 1']['klinkers'],
                    selected_names['Thuis speler 2']['klinkers'],
                    selected_names['Uit speler 1']['klinkers'],
                    selected_names['Uit speler 2']['klinkers']
                ]
                Uitslag.append_row(values)
                for team, player in selected_names.items():
                    if player['name'] == 'Kwint':
                        if ('Thuis' in team and away_score > home_score) | ('Uit' in team and home_score > away_score):
                            st.balloons()
                st.success("Uitslag toegevoegd!")

# Tabblad 2 #

with tab2:
    st.title(":crown: Ranglijst :crown:")

    Namen = pd.DataFrame(complete_list_of_players, columns=['Naam'])
    Uitslag = client.open('Tafelvoetbal').worksheet("Uitslag")
    all_values = Uitslag.get_all_values()
    # create a pandas DataFrame
    df = pd.DataFrame(all_values[1:], columns=all_values[0])

    df['Thuis_score'] = df['Thuis_score'].astype(int)
    df['Uit_score'] = df['Uit_score'].astype(int)
    df['Klinkers_thuis_1'] = df['Klinkers_thuis_1'].astype(int)
    df['Klinkers_thuis_2'] = df['Klinkers_thuis_2'].astype(int)
    df['Klinkers_uit_1'] = df['Klinkers_uit_1'].astype(int)
    df['Klinkers_uit_2'] = df['Klinkers_uit_2'].astype(int)

    # Punten per wedstrijd berekenen
    df['Thuis_punten'] = df.apply(lambda row:
                                  3 if (row['Thuis_score'] == 10 and row['Uit_score'] == 0) else (
                                      2 if row['Thuis_score'] == 10 else
                                      # 1.5 if row['Thuis_score'] == 9 else
                                      1), axis=1)

    df['Uit_punten'] = df.apply(lambda row:
                                3 if (row['Uit_score'] == 10 and row['Thuis_score'] == 0) else (
                                    # 1.5 if row['Uit_score'] == 9 else
                                    2 if row['Uit_score'] == 10 else
                                    1), axis=1)

    # calculate the score per player
    players = Namen['Naam'].tolist()
    players = [player for player in players if player not in ['Niemand', 'Niemanduit']]
    scores = ['Thuis_score', 'Uit_score']
    teams = ['Thuis_1', 'Thuis_2', 'Uit_1', 'Uit_2']
    punten = ['Thuis_punten', 'Uit_punten']
    klinkers = ['Klinkers_thuis_1', 'Klinkers_thuis_2', 'Klinkers_uit_1', 'Klinkers_uit_2']
    df_players = df[teams].apply(lambda x: x.str.strip())

    df_scores = df[scores].apply(pd.to_numeric)
    df_punten = df[punten].apply(pd.to_numeric)
    df_klinkers = df[klinkers].apply(pd.to_numeric)
    df_result = pd.DataFrame(index=players, columns=[
        'Gespeeld', 'Punten', 'Ratio', 'Voor', 'Tegen', 'Doelsaldo', 'Doelpunten gem.', 'Klinkers'
    ])

    for player in players:
        is_home = df_players['Thuis_1'] == player
        is_home |= df_players['Thuis_2'] == player

        is_away = df_players['Uit_1'] == player
        is_away |= df_players['Uit_2'] == player

        score_home = df_scores['Thuis_score'][is_home].sum()
        score_away = df_scores['Uit_score'][is_away].sum()

        score_not_home = df_scores['Uit_score'][is_home].sum()
        score_not_away = df_scores['Thuis_score'][is_away].sum()

        punten_home = df_punten['Thuis_punten'][is_home].sum()
        punten_away = df_punten['Uit_punten'][is_away].sum()

        klinkers_home_1 = df_klinkers['Klinkers_thuis_1'][df_players['Thuis_1'] == player].sum()
        klinkers_home_2 = df_klinkers['Klinkers_thuis_2'][df_players['Thuis_2'] == player].sum()
        klinkers_away_1 = df_klinkers['Klinkers_uit_1'][df_players['Uit_1'] == player].sum()
        klinkers_away_2 = df_klinkers['Klinkers_uit_2'][df_players['Uit_2'] == player].sum()

        df_result.loc[player, 'Voor'] = score_home + score_away
        df_result.loc[player, 'Tegen'] = score_not_home + score_not_away
        df_result.loc[player, 'Doelsaldo'] = score_home + score_away - score_not_home - score_not_away
        df_result.loc[player, 'Doelpunten gem.'] = ((score_home + score_away) / (sum(is_home) + sum(is_away))).round(2)
        df_result.loc[player, 'Punten'] = punten_home + punten_away
        df_result.loc[player, 'Gespeeld'] = sum(is_home) + sum(is_away)
        df_result.loc[player, 'Ratio'] = ((punten_home + punten_away) / (sum(is_home) + sum(is_away))).round(2)
        df_result.loc[player, 'Klinkers'] = klinkers_home_1 + klinkers_home_2 + klinkers_away_1 + klinkers_away_2

    df_result = df_result.sort_values(by=['Ratio', 'Doelpunten gem.', 'Gespeeld'], ascending=False)

    filter = st.number_input("Selecteer een minimum aantal wedstrijden",
                             min_value=0, max_value=20, value=3)

    # Filter the DataFrame based on the selected minimum number of points
    filtered_df_result = df_result[df_result['Gespeeld'] >= filter]

    # Display the filtered DataFrame
    st.dataframe(filtered_df_result)

    st.markdown("""<hr style="height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;" /> """,
                unsafe_allow_html=True)

    st.header("Alle uitslagen")
    players.sort()
    players.insert(0, 'Alle spelers')

    search_name = st.selectbox('Selecteer alle wedstrijden of van één specifieke speler:', players)

    # Filter the DataFrame based on the searched name
    if search_name != 'Alle spelers':
        filtered_df = df[
            df[['Thuis_1', 'Thuis_2', 'Uit_1', 'Uit_2']].apply(lambda x: x.str.contains(search_name, case=False)).any(
                axis=1)]
    else:
        filtered_df = df

    st.dataframe(filtered_df)

# Tabblad 3 #

with tab3:
    st.header("Voeg een speler toe")
    # Get the name from the user
    name = st.text_input("Vul een naam in:")
    # Add the name to the Google Sheet if the user clicks the button
    if st.button("Voeg naam toe"):
        add_name(name)

    st.markdown("""<hr style="height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;" /> """,
                unsafe_allow_html=True)

    # Display current known names
    st.header("Huidige namelijst")
    Namenlijst = client.open('Tafelvoetbal').worksheet("Namen")
    df_namen = pd.DataFrame(Namenlijst.col_values(1)[1:], columns=['Naam'])
    df_namen = df_namen.sort_values(by=['Naam'])
    df_namen.columns = ["Huidige namen"]
    st.table(df_namen)

# Tabblad 4 #

with tab4:
    # Create a dictionary to store player statistics
    player_stats = {}

    df_elo = df[~df[['Thuis_1', 'Thuis_2', 'Uit_1', 'Uit_2']].isin(['Niemand', 'Niemanduit']).any(axis=1)]


    # Define the ELO calculation function
    def elo_calculation(player_elo, opponent_elo, score, score_opp):

        k_factor = 64  # You can adjust this value as needed
        expected_outcome = 1 / (1 + 10 ** ((opponent_elo - player_elo) / 400))

        # Calculate the actual outcome based on the score difference
        score_difference = score - score_opp
        actual_outcome = 1 / (1 + 10 ** (-score_difference / 10))

        # Calculate ELO change based on the actual outcome
        elo_change = k_factor * (actual_outcome - expected_outcome)

        updated_elo = player_elo + elo_change
        return updated_elo


    match_ind = 1
    # Iterate through each row in the DataFrame
    for index, row in df_elo.iterrows():
        home_team = [row['Thuis_1'], row['Thuis_2']]
        away_team = [row['Uit_1'], row['Uit_2']]
        home_score = row['Thuis_score']
        away_score = row['Uit_score']
        timestamp = row['Timestamp']

        # Loop through home and away teams
        for team, score, opposing_team, opposing_score in [(home_team, home_score, away_team, away_score),
                                                           (away_team, away_score, home_team, home_score)]:
            elo_temp_match = {}
            for t in [team, opposing_team]:
                for player in t:
                    # Check if the player is already in the dictionary
                    if player not in player_stats:
                        player_stats[player] = []

                    # Calculate and update player statistics
                    elo = 1000 if not player_stats[player] else \
                        player_stats[player][-1][2]  # Initial ELO or previous ELO
                    elo_temp_match[player] = elo

            for player in team:
                # Check if the player is already in the dictionary
                if player not in player_stats:
                    player_stats[player] = []

                # Calculate and update player statistics
                match_index = match_ind
                elo = elo_temp_match[player]

                # Calculate opponent's ELO based on their current ELO (if available in player_stats)
                opponents = [p for p in opposing_team]  # Get the opponents

                opponent_elo = sum(elo_temp_match[opponent] for opponent in opponents) / 2
                # Calculate new ELO
                elo = round(elo_calculation(elo, opponent_elo, score, opposing_score), 0)
                # print(elo)

                total_goals = sum(stats[4] for stats in player_stats[player]) + score
                total_matches = len(player_stats[player]) + 1  # Total matches up until this point

                # Calculate average goals per match
                avg_goals_per_match = round(total_goals / total_matches, 2)

                player_stats[player].append(
                    [match_index, timestamp, elo, total_matches, score, total_goals, avg_goals_per_match])
                # player_stats[player][-1].append(opponents)
        match_ind += 1

    # Create a DataFrame 'df_player' with the latest stats for each player
    player_rows = []
    for player, stats in player_stats.items():
        latest_stat = stats[-1]  # Get the latest stats
        player_rows.append([player] + latest_stat)

    col = ['Speler', 'Wedstrijd Index', 'Timestamp', 'ELO', 'Totaal aantal wedstrijden', 'Doelpunten laatste wedstrijd',
           'Totaal aantal doelpunten', 'Gem aantal doelpunten per wedstrijd']
    df_player = pd.DataFrame(player_rows, columns=col)

    df_player = df_player.sort_values(by='ELO', ascending=False)

    # Display the player statistics DataFrame
    # Select a player using a Streamlit widget
    players_elo = sorted(list(player_stats.keys()))
    selected_player_elo = st.selectbox("Select a player:", players_elo)

    # Define a function to plot ELO development for a selected player

    def plot_elo_development(player_stat, selected_player_elo_f):
        elo_data = {
            "Match Index": [stats[3] for stats in player_stat[selected_player_elo_f]],
            "ELO Rating": [stats[2] for stats in player_stat[selected_player_elo_f]],
            "Doelpunten laatste wedstrijd": [stats[4] for stats in player_stat[selected_player_elo_f]]
        }

        df_elo = pd.DataFrame(elo_data)

        st.write(df_elo)

        st.line_chart(df_elo.set_index("Match Index"))


    # Plot ELO development for the selected player
    if selected_player_elo:
        plot_elo_development(player_stats, selected_player_elo)

    # df_player needs to be double checked!
    df_player = df_player[["Speler", "ELO", "Totaal aantal wedstrijden"]]

    st.write(df_player)
    st.write(player_stats)


# Tabblad 5 #

with tab5:
    st.title("Ruwe data google sheet")
    st.download_button(label="💾 Download volledige log", data=df.to_csv().encode('utf-8'),
                       file_name=get_download_filename('Tafelvoetbal_volledige_log', 'csv'), mime='text/csv')

    st.markdown("""<hr style="height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;" /> """,
                unsafe_allow_html=True)

    url = st.secrets["private_gsheets_url"].public_gsheets_url
    html = f'<iframe src="{url}" width="100%" height="100%" frameborder="0" scrolling="yes"></iframe>'

    st.markdown(html, unsafe_allow_html=True)

# Tabblad 6 #
with tab6:
    st.title("Verzoeken")
    st.write("Vul hier je verzoeken in voor extra functionaliteit")
    # Get the name from the user
    request = st.text_input("Vul een verzoek in:")
    # Add the name to the Google Sheet if the user clicks the button
    if st.button("Voeg verzoek toe"):
        add_request(request)

    st.markdown("""<hr style="height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;" /> """,
                unsafe_allow_html=True)

    # Display current known names
    st.header("Huidige verzoeken")
    # Access the worksheet
    verzoeken_lijst = client.open('Tafelvoetbal').worksheet("Verzoeken")
    all_values_verz = verzoeken_lijst.get_all_values()

    # Create a pandas DataFrame
    df_verzoeken = pd.DataFrame(all_values_verz[1:], columns=all_values_verz[0])

    # Display the DataFrame in a table
    st.table(df_verzoeken)

# Tabblad 7 #

with tab7:
    st.title("Colofon")
    st.write(Versie)
    st.write("Deze webapp is gemaakt met behulp van ChatGPT door Rick en Arthur")
