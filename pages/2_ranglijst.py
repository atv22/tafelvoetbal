import streamlit as st
import pandas as pd
from config import get_uitslag_df, get_players_list

from styles import setup_page

setup_page()
st.title(":crown: Ranglijst :crown:")
df = get_uitslag_df()
players = [p for p in get_players_list() if p not in ['Niemand', 'Niemanduit']]
# puntenregels
if not df.empty:
    df['Thuis_punten'] = df.apply(lambda row: 3 if (row['Thuis_score'] == 10 and row['Uit_score'] == 0)
                                  else (2 if row['Thuis_score'] == 10 else 1), axis=1)
    df['Uit_punten'] = df.apply(lambda row: 3 if (row['Uit_score'] == 10 and row['Thuis_score'] == 0)
                                else (2 if row['Uit_score'] == 10 else 1), axis=1)
    teams_cols = ['Thuis_1', 'Thuis_2', 'Uit_1', 'Uit_2']
    df_players = df[teams_cols].apply(lambda x: x.str.strip())
    scores = df[['Thuis_score', 'Uit_score']]
    punten = df[['Thuis_punten', 'Uit_punten']]
    klinkers = df[['Klinkers_thuis_1','Klinkers_thuis_2','Klinkers_uit_1','Klinkers_uit_2']]
    result_cols = ['Gespeeld','Punten','Ratio','Voor','Tegen','Doelsaldo','Doelpunten gem.','Klinkers']
    df_result = pd.DataFrame(index=players, columns=result_cols).fillna(0)
    for player in players:
        is_home = (df_players['Thuis_1'] == player) | (df_players['Thuis_2'] == player)
        is_away = (df_players['Uit_1'] == player) | (df_players['Uit_2'] == player)
        score_home = scores['Thuis_score'][is_home].sum()
        score_away = scores['Uit_score'][is_away].sum()
        score_not_home = scores['Uit_score'][is_home].sum()
        score_not_away = scores['Thuis_score'][is_away].sum()
        punten_home = punten['Thuis_punten'][is_home].sum()
        punten_away = punten['Uit_punten'][is_away].sum()
        klinkers_home_1 = klinkers['Klinkers_thuis_1'][df_players['Thuis_1'] == player].sum()
        klinkers_home_2 = klinkers['Klinkers_thuis_2'][df_players['Thuis_2'] == player].sum()
        klinkers_away_1 = klinkers['Klinkers_uit_1'][df_players['Uit_1'] == player].sum()
        klinkers_away_2 = klinkers['Klinkers_uit_2'][df_players['Uit_2'] == player].sum()
        gespeeld = int(is_home.sum() + is_away.sum())
        df_result.loc[player, 'Voor'] = int(score_home + score_away)
        df_result.loc[player, 'Tegen'] = int(score_not_home + score_not_away)
        df_result.loc[player, 'Doelsaldo'] = int(df_result.loc[player, 'Voor'] - df_result.loc[player, 'Tegen'])
        df_result.loc[player, 'Doelpunten gem.'] = round(df_result.loc[player, 'Voor'] / gespeeld, 2) if gespeeld else 0
        df_result.loc[player, 'Punten'] = int(punten_home + punten_away)
        df_result.loc[player, 'Gespeeld'] = gespeeld
        df_result.loc[player, 'Ratio'] = round(df_result.loc[player, 'Punten'] / gespeeld, 2) if gespeeld else 0
        df_result.loc[player, 'Klinkers'] = int(klinkers_home_1 + klinkers_home_2 + klinkers_away_1 + klinkers_away_2)
    df_result = df_result.sort_values(by=['Ratio','Doelpunten gem.','Gespeeld'], ascending=False)
    min_games = st.number_input("Selecteer een minimum aantal wedstrijden", min_value=0, max_value=20, value=3)
    st.dataframe(df_result[df_result['Gespeeld'] >= min_games])
    st.markdown("""<hr style=\"height:9px;border:none;color:#f0f2f6;background-color:#122f5b;opacity:0.8;\" />""", unsafe_allow_html=True)
    st.header("Alle uitslagen")
    players_sorted = sorted(players)
    players_sorted.insert(0, 'Alle spelers')
    search_name = st.selectbox('Selecteer alle wedstrijden of van één specifieke speler:', players_sorted)
    if search_name != 'Alle spelers':
        mask = df[teams_cols].apply(lambda x: x.str.contains(search_name, case=False)).any(axis=1)
        st.dataframe(df[mask])
    else:
        st.dataframe(df)
else:
    st.info("Nog geen wedstrijden geregistreerd.")
 