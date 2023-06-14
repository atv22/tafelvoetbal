import time
import datetime
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

Versie = "Beta versie 0.2.2 - 14 juni 2023"

st.set_page_config(page_title="Tafelvoetbal", page_icon="⚽", layout="centered", initial_sidebar_state="auto", menu_items=None)

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Invullen", "Ranglijst", "Spelers", "Ruwe data", "Verzoeken", "Colofon"])

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
            c1, c2 = st.columns([2,1])
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
    scores = ['Thuis_score', 'Uit_score']
    teams = ['Thuis_1', 'Thuis_2', 'Uit_1', 'Uit_2']
    punten = ['Thuis_punten', 'Uit_punten']
    klinkers = ['Klinkers_thuis_1', 'Klinkers_thuis_2', 'Klinkers_uit_1', 'Klinkers_uit_2']
    df_players = df[teams].apply(lambda x: x.str.strip())

    df_scores = df[scores].apply(pd.to_numeric)
    df_punten = df[punten].apply(pd.to_numeric)
    df_klinkers = df[klinkers].apply(pd.to_numeric)
    df_result = pd.DataFrame(index=players, columns=[
        'Gespeeld', 'Punten', 'Ratio', 'Voor', 'Tegen', 'Doelsaldo', 'Klinkers'
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
        df_result.loc[player, 'Punten'] = punten_home + punten_away
        df_result.loc[player, 'Gespeeld'] = sum(is_home) + sum(is_away)
        df_result.loc[player, 'Ratio'] = ((punten_home + punten_away) / (sum(is_home) + sum(is_away))).round(2)
        df_result.loc[player, 'Klinkers'] = klinkers_home_1+klinkers_home_2+klinkers_away_1+klinkers_away_2

    # df_result['Ratio'] = df_result['Ratio'].round(2)
    df_result = df_result.sort_values(by=['Ratio', 'Gespeeld', 'Doelsaldo'], ascending=False)
    st.dataframe(df_result)

    st.markdown("""<hr style="height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;" /> """, unsafe_allow_html=True)

    st.header("Alle uitslagen")
    players.insert(0, 'Alle spelers')
    search_name = st.selectbox('Selecteer alle wedstrijden of van één specifieke speler:', players)

    # Filter the DataFrame based on the searched name
    if search_name != 'Alle spelers':
        filtered_df = df[df[['Thuis_1', 'Thuis_2', 'Uit_1', 'Uit_2']].apply(lambda x: x.str.contains(search_name, case=False)).any(axis=1)]
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

    st.markdown("""<hr style="height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;" /> """, unsafe_allow_html=True)

    # Display current known names
    st.header("Huidige namelijst")
    Namenlijst = client.open('Tafelvoetbal').worksheet("Namen")
    df_namen = pd.DataFrame(Namenlijst.col_values(1)[1:], columns=['Naam'])
    df_namen = df_namen.sort_values(by=['Naam'])
    df_namen.columns = ["Huidige namen"]
    st.table(df_namen)

# Tabblad 4 #

with tab4:
    st.title("Ruwe data google sheet")
    st.download_button(label="💾 Download volledige log", data = df.to_csv().encode('utf-8'),
                       file_name=get_download_filename('Tafelvoetbal_volledige_log', 'csv'), mime='text/csv')

    st.markdown("""<hr style="height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity: 0.8;" /> """,
                unsafe_allow_html=True)


    url = st.secrets["private_gsheets_url"].public_gsheets_url
    html = f'<iframe src="{url}" width="100%" height="100%" frameborder="0" scrolling="yes"></iframe>'

    st.markdown(html, unsafe_allow_html=True)

# Tabblad 5 #
with tab5:
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


# Tabblad 6 #

with tab6:
    st.title("Colofon")
    st.write(Versie)
    st.write("Deze webapp is gemaakt met behulp van ChatGPT door Rick en Arthur")