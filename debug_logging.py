import app
def main():
    _, _, _, _, beheer_log_df, _ = app.load_all_data(app.CACHE_VERSION)
    print("Beheer log size:", len(beheer_log_df))
    if not beheer_log_df.empty:
        print(beheer_log_df.head())

if __name__ == '__main__':
    main()
