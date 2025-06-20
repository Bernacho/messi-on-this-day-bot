import pandas as pd
import time
from datetime import datetime, UTC, timedelta


from goal_plot import *
from goal_tweet import *

PROCESSING_TIME_SEC = 30
WAITING_MINUTES = 4

def check_and_tweet():
    now = datetime.now(UTC).replace(second=0,microsecond=0)
    end = now + timedelta(minutes=WAITING_MINUTES)
    today = now.date()

    print(f"Checking schedule at {now}")

    df = pd.read_csv("data/messi_goals_with_goal_datetime.csv")
    df['goal_datetime'] = pd.to_datetime(df.goal_datetime).apply(lambda x: x.replace(year=today.year))
    df['time'] = df.goal_datetime.dt.time
    df['goal_datetime'] = df['goal_datetime'].dt.floor("min")

    matching_goals = df[df.goal_datetime.between(now,end,inclusive='both')].sort_values(["goal_datetime","time"]).reset_index(drop=True)

    for i, g_ in matching_goals.iterrows():
        print(f"Tweeting goal: {g_.id}")
        text_, gif_file_ = create_tweet(g_)
        publish_tweet(text_, gif_file_)
        if g_.wait_min<=WAITING_MINUTES:
            time.sleep((g_.wait_min*60) - ((i+1)*PROCESSING_TIME_SEC))

if __name__ == "__main__":
    check_and_tweet()