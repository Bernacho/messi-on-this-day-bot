import pandas as pd
import schedule
import time
from datetime import datetime, UTC


from goal_plot import *
from goal_tweet import *


def check_and_tweet():
    now = datetime.now(UTC).replace(second=0,microsecond=0)
    today = now.date()

    df = pd.read_csv("data/messi_goals_with_goal_datetime.csv")
    df['goal_datetime'] = pd.to_datetime(df.goal_datetime).apply(lambda x: x.replace(year=today.year)).dt.floor("min")

    matching_goals = df[df.goal_datetime==now]
    for i, g_ in matching_goals.iterrows(g_):
        text_, gif_file_ = create_tweet(text_, gif_file_)
        publish_tweet(text_, gif_file_)

    pass

schedule.every(1).minutes.do(check_and_tweet)

while True:
    schedule.run_pending()
    time.sleep(30)