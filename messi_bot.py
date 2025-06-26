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
    MAX_RETRIES = 3
    PUBLISHED_TWEETS = 0

    now = datetime.now(UTC).replace(second=0,microsecond=0)
    # end = now + timedelta(minutes=WAITING_MINUTES)
    today = now.date()

    print(f"Checking schedule at {now}")

    df = pd.read_csv("data/messi_goals_with_goal_datetime.csv")

    df['goal_datetime'] = pd.to_datetime(df.goal_datetime).apply(lambda x: x.replace(year=today.year))
    df['goal_datetime_floor'] = df.goal_datetime.copy().dt.floor("min")

    matching_goals = df[df.goal_datetime_floor==now].sort_values(["goal_datetime"]).reset_index(drop=True)
    
    for i, g_ in matching_goals.iterrows():
        # No waiting
        # if i==0:
        #     wait_sec = (g_.goal_datetime - now).total_seconds()
        # else:
        #     wait_sec = g_.wait_sec - PROCESSING_TIME_SEC
        # time.sleep(max(0,wait_sec))
        
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"Tweeting goal: {g_.id}")
                text_, gif_file_ = create_tweet(g_)
                publish_tweet(text_, gif_file_)
                PUBLISHED_TWEETS+=1
                break
            except Exception as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt == MAX_RETRIES:
                    print("All retry attempts failed.")


    if PUBLISHED_TWEETS>0:
        m_ = f"{PUBLISHED_TWEETS} Tweets {now}"
    else:
        m_ = f"No goals found {now}"
    print(m_)

    return m_


if __name__ == '__main__':
    app.run()