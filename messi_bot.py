import pandas as pd
import time
from datetime import datetime, UTC, timedelta
from flask import Flask


from goal_plot import *
from goal_tweet import *

PROCESSING_TIME_SEC = 20
WAITING_MINUTES = 0

app = Flask(__name__)

@app.route("/check_goals")
def check_and_tweet():
    now = datetime.now(UTC).replace(second=0,microsecond=0)
    end = now + timedelta(minutes=WAITING_MINUTES)
    today = now.date()

    print(f"Checking schedule at {now}")

    df = pd.read_csv("data/messi_goals_with_goal_datetime.csv")

    df['goal_datetime'] = pd.to_datetime(df.goal_datetime).apply(lambda x: x.replace(year=today.year))
    df['goal_datetime_floor'] = df.goal_datetime.copy().dt.floor("min")

    # matching_goals = df[df.goal_datetime_floor.between(now,end,inclusive='both')].sort_values(["goal_datetime"]).reset_index(drop=True)
    matching_goals = df[df.goal_datetime_floor.dt.date==today].sort_values(["goal_datetime"]).reset_index(drop=True)

    for i, g_ in matching_goals.iterrows():
        # No waiting
        # if i==0:
        #     wait_sec = (g_.goal_datetime - now).total_seconds()
        # else:
        #     wait_sec = g_.wait_sec - PROCESSING_TIME_SEC
        # time.sleep(max(0,wait_sec))
        
        print(f"Tweeting goal: {g_.id}")
        text_, gif_file_ = create_tweet(g_)
        publish_tweet(text_, gif_file_)

    l_=matching_goals.shape[0]
    if l_>0:
        m_ = f"{l_} Tweets {now}"
    else:
        m_ = f"No goals found {now}"
    
    print(m_)
    return m_


if __name__ == '__main__':
    app.run()