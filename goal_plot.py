import pandas as pd
from datetime import datetime
from mplsoccer import VerticalPitch,Pitch,inset_axes
import numpy as np
from matplotlib import pyplot as plt
import os
from PIL import Image, ImageSequence
from matplotlib.animation import FuncAnimation
from matplotlib.animation import PillowWriter
import matplotlib.font_manager as fm
import matplotlib as mpl
from matplotlib.lines import Line2D

KEPT_EVENTS = ['Pass','Ball Receipt','Carry','Shot','Ball Recovery','Interception','Block','Clearence','Dispossessed','Goal Keeper']
MIN_GOAL_SEQUENCE_LENGHT_SEC = 5
MAX_GOAL_SEQUENCE_LENGHT_SEC = 15
LAST_FRAME_DURATION_SEC = 5
PENULTIMATE_FRAME_DURATION_SEC = 1


font_path = "./fonts/Inter_18pt-Regular.ttf"
inter_font = fm.FontProperties(fname=font_path)
fm.fontManager.addfont(font_path)
bold_path = "./fonts/Inter_18pt-Bold.ttf"
bold_font = fm.FontProperties(fname=bold_path)
fm.fontManager.addfont(bold_path)
mpl.rcParams['font.family'] = inter_font.get_name()

def infer_attack_direction(events_df, team_name, period=1):

    # Filter for team events in the selected period
    filtered = events_df[
        (events_df['period'] == period) &
        (events_df['type_name'].isin(['Pass', 'Carry', 'Shot'])) &
        (~events_df['x'].isnull())
    ]

    if filtered.empty or (period>4):
        return "left_to_right"

    avg_x = filtered.groupby("team_name")['x'].mean()


    if avg_x[team_name] >= (avg_x.sum() - avg_x[team_name]):
        direction = 'left_to_right'
    else:
        direction = 'right_to_left'

    return direction

def get_timedelta(t1,t2):
    t2_ = datetime.combine(datetime.today(),t2)
    t1_ = datetime.combine(datetime.today(),t1)

    return (t2_ - t1_).total_seconds()

def get_goal_sequence(goal,all_events,tactics):
    goal_events = all_events[all_events.possession==goal.possession].loc[lambda y: y.type_name.isin(KEPT_EVENTS)].sort_values("index")
    # limit here the sequence length ?

    first_ = goal_events.iloc[0]
    last_ =goal_events.iloc[-1]

    elapsed_time = get_timedelta(first_.timestamp,last_.timestamp)
    first_possession = first_.possession

    while (elapsed_time < MIN_GOAL_SEQUENCE_LENGHT_SEC) & (first_possession>1) & (goal.sub_type_name not in ['Penalty','Free Kick']):
        first_possession -= 1
        goal_events = all_events[all_events.possession.between(first_possession,goal.possession)].loc[lambda y: y.type_name.isin(KEPT_EVENTS)].sort_values("index")
        goal_events['elapsed_time'] = goal_events.timestamp.apply(lambda y: get_timedelta(y,goal.timestamp))
        goal_events = goal_events[goal_events.elapsed_time<= MAX_GOAL_SEQUENCE_LENGHT_SEC]
        first_ = goal_events.iloc[0]
        last_ =goal_events.iloc[-1]
        elapsed_time = get_timedelta(first_.timestamp,last_.timestamp)
        first_possession = first_.possession

    jersey_numbers = tactics.groupby('player_id').jersey_number.first()
    goal_events['jersey_number'] = goal_events.player_id.map(jersey_numbers)
    goal_events.reset_index(drop=True,inplace=True)
    goal_ = goal_events[goal_events.outcome_name=="Goal"].iloc[0]
    
    return goal_events.loc[:goal_.name]

night_match_palette = {
    "pitch":"#29274C", #"#1A237E",
    "pitch_contrast":"#0D47A1",
    "lines": "#E0F7FA",
    # "marker_primary":"#FFEB3B",
    "marker_primary":"#00E5FF",
    "marker_secondary":"#EF7A85",
    "marker_highlight":"#FF4081",
    "text":"#FAFAFA",
    "text_secondary":"#B3E5FC",
}

paletts = {"night_match":night_match_palette}

def get_pitch(palette_="night_match",vertical=False,stripe=False):
    palette_ = paletts[palette_]
    line_width = 3 #if not white_pitch else 2

    if not vertical:
        pitch = Pitch(pitch_type='statsbomb', corner_arcs=True,stripe=stripe,stripe_color=palette_['pitch_contrast'],
                    pitch_color=palette_['pitch'], line_color=palette_['lines'],linewidth=line_width,line_zorder=2)
    else:
        pitch = VerticalPitch(pitch_type='statsbomb', corner_arcs=True,stripe=stripe,stripe_color=palette_['pitch_contrast'],
                    pitch_color=palette_['pitch'], line_color=palette_['lines'],linewidth=line_width,line_zorder=2)
    return pitch

def shorten_arrow(x1, y1, x2, y2, r=1,type="end"):
    """Shorten the arrow by a given length."""
    dx = x2 - x1
    dy = y2 - y1
    # dist = (dx**2 + dy**2)**0.5
    dist = np.hypot(dx,dy)
    if dist == 0:
        return x2, y2  
    factor = (dist - r) / dist
    if type=="end":
        new_x2 = x1 + dx * factor
        new_y2 = y1 + dy * factor
    else:
        new_x2 = x2 - dx * factor
        new_y2 = y2 - dy * factor
    return new_x2,new_y2

def format_events(events_,attack_direction,receipt_radius=2.5):
    goal_ = events_[events_.outcome_name=="Goal"].iloc[0]
    team_= goal_.team_name

    # mirror events
    if attack_direction == "right_to_left":
        events_.loc[(events_.team_name==team_) & (events_.x.notna()),'x'] = 120 - events_.loc[(events_.team_name==team_) & (events_.x.notna()),'x']
        events_.loc[(events_.team_name==team_) & (events_.end_x.notna()),'end_x'] = 120 - events_.loc[(events_.team_name==team_) & (events_.end_x.notna()),'end_x']
        events_.loc[(events_.team_name==team_) & (events_.y.notna()),'y'] = 80 - events_.loc[(events_.team_name==team_) & (events_.y.notna()),'y']
        events_.loc[(events_.team_name==team_) & (events_.end_y.notna()),'end_y'] = 80 - events_.loc[(events_.team_name==team_) & (events_.end_y.notna()),'end_y']
    else:
        events_.loc[(events_.team_name!=team_) & (events_.x.notna()),'x'] = 120 - events_.loc[(events_.team_name!=team_) & (events_.x.notna()),'x']
        events_.loc[(events_.team_name!=team_) & (events_.end_x.notna()),'end_x'] = 120 - events_.loc[(events_.team_name!=team_) & (events_.end_x.notna()),'end_x']
        events_.loc[(events_.team_name!=team_) & (events_.y.notna()),'y'] = 80 - events_.loc[(events_.team_name!=team_) & (events_.y.notna()),'y']
        events_.loc[(events_.team_name!=team_) & (events_.end_y.notna()),'end_y'] = 80 - events_.loc[(events_.team_name!=team_) & (events_.end_y.notna()),'end_y']

    # resize arrows for Passes
    events_.loc[lambda x: x.type_name=="Pass","new_end"] = events_.loc[lambda x: x.type_name=="Pass",:].apply(lambda y: shorten_arrow(y.x,y.y,y.end_x,y.end_y,receipt_radius,"end"),axis=1)
    events_.loc[lambda x: x.type_name=="Pass","new_start"] = events_.loc[lambda x: x.type_name=="Pass",:].apply(lambda y: shorten_arrow(y.x,y.y,y.end_x,y.end_y,receipt_radius,"start"),axis=1)
    if events_.loc[lambda x: x.type_name=="Pass",:].shape[0]>0:
        events_.loc[lambda x: x.type_name=="Pass","new_end_x"] = events_.loc[lambda x: x.type_name=="Pass","new_end"].str[0].astype(float)
        events_.loc[lambda x: x.type_name=="Pass","new_end_y"] = events_.loc[lambda x: x.type_name=="Pass","new_end"].str[1].astype(float)
        events_.loc[lambda x: x.type_name=="Pass","new_start_x"] = events_.loc[lambda x: x.type_name=="Pass","new_start"].str[0].astype(float)
        events_.loc[lambda x: x.type_name=="Pass","new_start_y"] = events_.loc[lambda x: x.type_name=="Pass","new_start"].str[1].astype(float)
    

    return events_

def events_to_frames(events_,palette_="night_match"):
    frames_ = []
    frames_duration_=[]
    n = len(events_)
    palette_ = paletts[palette_]

    goal_ = events_[events_.outcome_name=="Goal"].iloc[0]
    team_= goal_.team_name

    events_['color'] = palette_['marker_primary']
    events_['color'] = events_['color'].mask(events_.team_name!=team_,palette_['marker_secondary'])

    lines_ = []
    arrows_ = []
    scatter_ = []
    annotations_=[]

    for i,event in events_.iterrows():
        plot_scatter = None
        plot_annotation = None
        plot_line = None
        plot_arrow = None

        plot_player = (i==0)
        if i>0:
            past_event = events_.iloc[i-1]
            plot_player = (event.team_name,event.jersey_number)!=(past_event.team_name,past_event.jersey_number)
        
        # marker
        # if (event.type_name in ["Ball Receipt","Ball Recovery",'Carry']) or (i==0):
        if plot_player:
            plot_scatter = [(event.x,event.y),event.color,"o",5]
            plot_annotation =[(event.x,event.y),event.jersey_number,palette_['pitch'] if event.team_name==team_ else palette_['text'],5]
        # Lines and arrows
        if (event.type_name in ['Pass','Clearence']) & (pd.isna(event.end_x)==False):
            ls = "-" if pd.isna(event.outcome_name) else "--"
            plot_arrow =[(event.x,event.y),(event.new_end_x,event.new_end_y),event.color,ls,3,2]
        elif event.type_name == 'Carry':
            plot_line = [(event.x,event.y),(event.end_x,event.end_y),event.color,"--",3,False,2]
        elif event.type_name == 'Shot':
            c_ = palette_['marker_highlight'] if event.outcome_name=="Goal" else palette_['text_secondary']
            plot_arrow = [(event.x,event.y),(event.end_x,event.end_y),c_,"-",4,3]
        elif event.type_name=="Dispossessed":
            plot_scatter = [(event.x,event.y),event.color,"x",3]
            
        # elif event.type_name =='Ball Recovery':
        #     pitch.scatter(event.x, event.y, s=50, color=event.color, ax=ax)
        # elif event.type_name =='Dispossessed':
        #     pitch.scatter(event.x, event.y, s=50*2,ls="--", edgecolor=event.color,color=None, ax=ax)
        # elif event.type_name == 'Interception':
        #     pitch.scatter(event.x, event.y, s=50, color='purple', ax=ax)
        # elif event.type_name == 'Block':
        #     pitch.scatter(event.x, event.y, s=50, color='brown', ax=ax)
        # elif event.type_name == 'Clearence':
        #     pitch.scatter(event.x, event.y, s=50, color='pink', ax=ax)
            
        if plot_scatter is not None:
            scatter_.append(plot_scatter)
        if plot_line is not None:
            lines_.append(plot_line)
        if plot_arrow is not None:
            arrows_.append(plot_arrow)
        if plot_annotation is not None:
            annotations_.append(plot_annotation)
            
        if i==(n-1):
            interval_ = PENULTIMATE_FRAME_DURATION_SEC if i>0 else LAST_FRAME_DURATION_SEC
        else:
            next_event = events_.iloc[i+1]
            interval_ = get_timedelta(event.timestamp, next_event.timestamp)
            if interval_<=0:
                continue 
        
        frames_duration_.append(interval_)
        frames_.append([lines_,arrows_,scatter_,annotations_])
        lines_,arrows_,scatter_,annotations_ = [],[],[],[]
    
    g_ = events_[events_.outcome_name=="Goal"].iloc[0]
    xg_ = g_.shot_statsbomb_xg
    xg_annotation =[(60,-2),"" if pd.isna(xg_) else f"Shot expected goals: {xg_:.1%}",palette_['lines'],5]
    if len(frames_)==1:
        frames_[0][3].append(xg_annotation)
    else:
        last_frame = [[],[],[],[xg_annotation]]
        frames_.append(last_frame)
        frames_duration_.append(LAST_FRAME_DURATION_SEC)


    assert len(frames_)==len(frames_duration_), "Frames and frames duation of different sizes"
    return frames_,frames_duration_

def plot_elements(frame_,pitch_,ax_,receipt_radius=2.5,scale_factor=40):
    lines_,arrows_,scatter_,annotations_ = [],[],[],[]

    for l in frame_[0]:
        p = pitch_.lines(l[0][0],l[0][1],l[1][0],l[1][1],color=l[2],ls=l[3],lw=l[4],comet=l[5],zorder=l[6],ax=ax_)
        lines_.append(p)
    for arrow in frame_[1]:
        p = pitch_.arrows(arrow[0][0],arrow[0][1],arrow[1][0],arrow[1][1],color=arrow[2],ls=arrow[3],width=arrow[4],zorder=arrow[5],ax=ax_)
        arrows_.append(p)
    for s in frame_[2]:
        p = pitch_.scatter(s[0][0],s[0][1],s=np.pi*(receipt_radius**2)*scale_factor,color=s[1],marker=s[2],ax=ax_,zorder=s[3])
        scatter_.append(p)
    for a in frame_[3]:
        p = pitch_.annotate(a[1],xy=(a[0][0],a[0][1]),color=a[2],zorder=a[3],ax=ax_,
                        ha="center",va='center',fontproperties=bold_font,fontsize=16)
        annotations_.append(p)

    return lines_, arrows_, scatter_, annotations_

def gif_with_durations(durations_):
    gif = Image.open("gif/temp.gif")
    new_frames = []
    for i, frame in enumerate(ImageSequence.Iterator(gif)):
        frame = frame.copy()
        frame.info['duration'] = durations_[i] * 1000
        new_frames.append(frame)

    file_ = "gif/goal_animation.gif"
    # if os.path.exists(file_):
    #     os.remove(file_)
    new_frames[0].save(file_, save_all=True, append_images=new_frames[1:], loop=0)
    gif.close()
    return file_

def goal_view_plot(g_,ax,side='left_to_right',palette_="night_match"):
    palette_ = paletts[palette_]

    inset_width,inset_height= (50,30)
    inset_ax = inset_axes(x=30 + (0 if side=='left_to_right' else 60), y=40, width=inset_width, height=inset_height, ax=ax,zorder=3)

    # Set axis limits to match your StatsBomb goal coordinates
    inset_ax.set_xlim(36.34-0.5, 43.66+0.5)  # Left to right (shooter’s view)
    inset_ax.set_ylim(0-0.5, 2.44+1)      # Ground to crossbar

    # Make sure the aspect ratio is equal
    inset_ax.set_aspect('equal')
    # Draw goalposts and crossbar
    post_color = palette_['pitch']
    left_post = Line2D([36.34, 36.34], [0, 2.44], color=post_color, linewidth=4)
    right_post = Line2D([43.66, 43.66], [0, 2.44], color=post_color, linewidth=4)
    crossbar = Line2D([36.34, 43.66], [2.44, 2.44], color=post_color, linewidth=4)
    ground = Line2D([36.34, 43.66], [0, 0], color=post_color, linestyle='--')

    inset_ax.add_line(left_post)
    inset_ax.add_line(right_post)
    inset_ax.add_line(crossbar)
    inset_ax.add_line(ground)

    # Optional: remove axis ticks and labels
    inset_ax.set_xticks([])
    inset_ax.set_yticks([])
    for spine in inset_ax.spines.values():
        spine.set_visible(False)

    inset_ax.scatter(g_.end_y,g_.end_z,s=250,zorder=3,color=palette_['marker_highlight'],edgecolors=palette_['marker_highlight'])

    #style
    center_x = inset_ax.get_xlim()[0]+((inset_ax.get_xlim()[1] - inset_ax.get_xlim()[0])/2)
    inset_ax.annotate("Goal view",xy=(center_x,2.94),ha='center',va='center',color=palette_['pitch'],fontsize=14,fontproperties=bold_font)
    inset_ax.set_facecolor(palette_['marker_primary'])

def plot_goal(events_,all_events_,palette_="night_match",stripe_=False,vertical_=False):
    receipt_radius = 3
    scale_factor = 35
    alpha=0.4
    text_alpha=0.75
    goal = events_[events_.outcome_name=="Goal"].iloc[0]
    team = goal.team_name
    attack_direction = infer_attack_direction(all_events_,team,goal.period)
    events_ = format_events(events_.copy(),attack_direction,receipt_radius)
    # return events_
    pitch = get_pitch(palette_,stripe=stripe_,vertical=vertical_)
    fig, ax = pitch.draw(figsize=(12,8))

    if goal.sub_type_name in ['Penalty','Free Kick']:
        goal_view_plot(goal,ax,attack_direction,palette_)
        
    frames_,frames_duration_ = events_to_frames(events_,palette_)
    
    lines = []
    arrows = []
    scatter = []
    annotations = []

    def update_plot(i):
        frame = frames_[i]
        dur = frames_duration_[i]        
        anim.event_source.interval = dur * 1000
       
        li,ar,sc,an = plot_elements(frame,pitch,ax,receipt_radius,scale_factor)

        for l in li:
            lines.append(l)
        for arr in ar:
            arrows.append(arr)
        for s in sc:
            scatter.append(s)
        for a in an:
            annotations.append(a)

        scatter_limit =-1 if len(sc)==0 else -len(sc)
        for l in lines[:-len(li)]:
            l.set_alpha(alpha)
        for a in arrows[:-len(ar)]:
            a.set_alpha(alpha)
        for s in scatter[:scatter_limit]:
            s.set_alpha(alpha)
        for a in annotations[:scatter_limit]:
            a.set_alpha(text_alpha)
        
        return lines + arrows + scatter + annotations
   

    n_frames = range(len(frames_))
    anim = FuncAnimation(fig, update_plot, frames=n_frames,blit=False,interval=5000)
    file_name_ = "gif/temp.gif"
    # if os.path.exists(file_name_):
    #     os.remove(file_name_)
    writer = PillowWriter(fps=1)
    anim.save(file_name_, writer=writer)

    new_file_name = gif_with_durations(frames_duration_)
    plt.close(fig)

    return new_file_name