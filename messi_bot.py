import pandas as pd
import time
from datetime import datetime, UTC, timedelta


from goal_plot import *
from goal_tweet import *

SETUP_TIME_SEC = 25
PROCESSING_TIME_SEC = 20
WAITING_MINUTES = 4

def check_and_tweet():
    now = datetime.now(UTC).replace(second=0,microsecond=0)
    end = now + timedelta(minutes=WAITING_MINUTES)
    today = now.date()

    print(f"Checking schedule at {now}")

    df = pd.read_csv("data/messi_goals_with_goal_datetime.csv")

    df['goal_datetime'] = pd.to_datetime(df.goal_datetime).apply(lambda x: x.replace(year=today.year))
    df['goal_datetime_floor'] = df.goal_datetime.copy().dt.floor("min")

    matching_goals = df[df.goal_datetime_floor.between(now,end,inclusive='both')].sort_values(["goal_datetime"]).reset_index(drop=True)

    for i, g_ in matching_goals.iterrows():
        if i==0:
            wait_sec = (g_.goal_datetime - now).total_seconds() - SETUP_TIME_SEC
        else:
            wait_sec = g_.wait_sec - PROCESSING_TIME_SEC

        time.sleep(max(0,wait_sec))

        print(f"Tweeting goal: {g_.id}")
        text_, gif_file_ = create_tweet(g_)
        publish_tweet(text_, gif_file_)


if __name__ == "__main__":
    check_and_tweet()