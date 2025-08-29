import random
import pandas as pd
from statsbombpy import sb
from mplsoccer import Sbopen
from dotenv import load_dotenv
import os
import tweepy
from goal_plot import *

GOAL_SHOUT_TEXT = [
    "Messi scores!",
    "Goal by Messi!",
    "Goal! Messi!",
    "Meeeeeeessssssiiiiiii!!!!",
    "Goal by the GOAT! \U0001F410",
    "Messi does it one more time!",
    "WHAT?!?!?! Messi scores!",
    "It's Messi again!",
    "Strike by Messi!",
    "Lionel scores!",
    "Lionel delivers!",
    "Netbuster by Messi!",
    "Bang-Messi scores!",
    "Classic Messi magic!",
    "Messi finds the net!",
    "LEEEEEEEOOOOOOO!!!!!",
    "He makes it look easy-Messi!",
    "The maestro scores!",
    "Goal by the little genius!",
    "SADFKJGDSALJASDLK#@%LKJLKAMLQW#AWEKF6LNADSLJ!!!!",
    "\U0001F410\U0001F410\U0001F410\U0001F410\U0001F410"
]

PENALTY_SHOUT_TEXT = [
    "Messi scores his penalty!",
    "Messi does not miss from the penalty spot!",
    "Messi converts the penalty!",
    "Goal! Messi scores his pen!",
    "YEEEEESSS!!! Messi scores the penlaty!"
]

FREEKICK_SHOUT_TEXT = [
    "Messi scores from a freekick!",
    "WHAAAATTT?!?!?!? He puts it in the net from miles away!",
    "Goal! What a freekick from Messi!",
    "Messi scores from a freekick! No one takes them like him!",
    "Unreal freekick by Messi! What a Goal!"
]

HASHTAGS = ["#SoccerAnalytics", "#FootballData", "#xG", "#DataViz", "#ExpectedGoals","#Messi", "#GOAT", "#OnThisDay",
            "#StatsBomb", "#AnalyticsFC","#StatsFC","#FootballTwitter","#BeautifulGame"]

def get_goal_events(e):
    _goals = e[e.outcome_name=="Goal"]
    _own_goals = e[e.type_name=="Own Goal For"]

    return pd.concat([_goals,_own_goals])

def get_goal_tweet(goal_,match_,all_goals_):
    date = match_.match_date
    period = goal_.period
    minute = goal_.minute
    second = goal_.second

    home_team = match_.home_team.upper() if goal_.team_name==match_.home_team else match_.home_team
    away_team = match_.away_team.upper() if goal_.team_name==match_.away_team else match_.away_team

    score = all_goals_[((all_goals_.period<period)   | ((all_goals_.period==period) & (all_goals_.timestamp<=goal_.timestamp))) & (all_goals_.period<=4) ].groupby("team_name").size()
    if match_.home_team not in score.index:
        score[match_.home_team] = 0
    if match_.away_team not in score.index:
        score[match_.away_team] = 0

    penalties = None
    if period>4:
        penalties = all_goals_[((all_goals_.period<period)   | ((all_goals_.period==period) & (all_goals_.timestamp<=goal_.timestamp))) & (all_goals_.period>4) ].groupby("team_name").size()
        if match_.home_team not in penalties.index:
            penalties[match_.home_team] = 0
        if match_.away_team not in penalties.index:
            penalties[match_.away_team] = 0

    if penalties is None:
        score_text  = f"{home_team} {score[match_.home_team]} - {away_team} {score[match_.away_team]}"
    else:
        score_text  = f"{home_team} {score[match_.home_team]} ({penalties[match_.home_team]}) - {away_team} {score[match_.away_team]} ({penalties[match_.away_team]})"


    competition = match_.competition
    shout = random.choice((PENALTY_SHOUT_TEXT if goal_.sub_type_name=="Penalty" else (FREEKICK_SHOUT_TEXT if goal_.sub_type_name=="Free Kick" else GOAL_SHOUT_TEXT)))
    max_time = {1:45,2:90,3:105,4:120,5:1000,6:1000}
    display_minute = min(minute,max_time[period])
    added_minute = minute - display_minute
    added_second = second if minute>=max_time[period] else 0
    if (added_minute==0) and (added_second==0):
        time = f"{minute}:{str(second).zfill(2)}"
    else:
        time = f"{display_minute}+{added_minute}:{str(added_second).zfill(2)}"

    tweet_text = f"[{date}] {shout} ({time}). {score_text}, {competition}"
    tweet_text = tweet_text + "\n\n" + " ".join(random.sample(HASHTAGS+(["#LaLiga"] if "La Liga" in competition else []),2))
    
    return tweet_text

def create_tweet(g_):
        parser = Sbopen()

        match = sb.matches(competition_id=g_.competition_id, season_id=g_.season_id).loc[lambda x: x.match_id==g_.match_id].iloc[0]
        events, __,___,_ = parser.event(g_.match_id)
        lineups = list(sb.lineups(g_.match_id).values())
        lineup = pd.concat(lineups,axis=0)
        all_goals = get_goal_events(events)
        goal = all_goals[all_goals.id==g_.id].iloc[0]
        text = get_goal_tweet(goal,match,all_goals)
        goal_sequence = get_goal_sequence(goal,events,lineup)
        file = plot_goal(goal_sequence,events,stripe_=False)

        return text, file

def publish_tweet(text_, file_):
    load_dotenv() 

    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    ACCESS_SECRET = os.getenv("ACCESS_SECRET")

    auth = tweepy.OAuth1UserHandler(
        API_KEY,
        API_SECRET,
        ACCESS_TOKEN,
        ACCESS_SECRET
    )
    api_v1 = tweepy.API(auth)

    media = api_v1.media_upload(file_)

    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET
    )

    client.create_tweet(
        text=text_,
        media_ids=[media.media_id]
    )