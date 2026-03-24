"""
TAB COMMITS: Module om de laatste GitHub commits te tonen
"""
import streamlit as st
import subprocess
import pandas as pd

def get_git_commits(limit=50):
    """Haal de laatste git commits op via de command line."""
    try:
        # Gebruik git log om commits op te halen in een specifiek formaat
        # %h: short hash, %ad: author date, %an: author name, %s: subject
        cmd = ["git", "log", f"-n {limit}", "--pretty=format:%h|%ad|%an|%s", "--date=short"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        lines = result.stdout.strip().split("\n")
        commits = []
        for line in lines:
            if "|" in line:
                parts = line.split("|")
                if len(parts) == 4:
                    commits.append({
                        "Hash": parts[0],
                        "Datum": parts[1],
                        "Auteur": parts[2],
                        "Bericht": parts[3]
                    })
        return pd.DataFrame(commits)
    except Exception as e:
        st.error(f"Fout bij het ophalen van commits: {e}")
        return pd.DataFrame()

def render_commits_tab():
    """Render de Commits tab."""
    st.header("📜 Commit Historie")
    st.write("Overzicht van de laatste wijzigingen in de applicatie.")

    commits_df = get_git_commits()

    if not commits_df.empty:
        # Toon de commits in een nette tabel
        st.dataframe(
            commits_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Geen commit historie gevonden of git is niet beschikbaar.")
