"""Cymru Form Tracker — clean local Streamlit dashboard.
Uses output CSVs only. No API calls, no identity approval changes.
Run: python -m streamlit run welsh_dashboard.py
"""
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Cymru Form Tracker',page_icon='⚽',layout='wide',initial_sidebar_state='expanded')
BASE=Path(__file__).resolve().parent
OUT=BASE/'data' if (BASE/'data'/'leaderboard.csv').exists() else BASE/'output'
PUBLIC_MODE=OUT.name=='data'

# A deliberately restrained visual system: a single primary teal, with muted
# violet and amber accents. Cell fills convey the data, not decoration.
st.markdown('''<style>
.block-container {padding-top:1.5rem;max-width:1460px;padding-bottom:3.5rem}
h1,h2,h3 {letter-spacing:-.035em}
h1 {font-size:2.25rem!important;font-weight:730!important}
[data-testid="stMetric"] {border:1px solid rgba(128,145,155,.18);border-radius:12px;padding:13px 16px;background:rgba(125,153,166,.055)}
[data-testid="stMetricLabel"] {font-size:.8rem}
[data-testid="stMetricValue"] {font-size:1.65rem}
[data-testid="stSidebar"] {border-right:1px solid rgba(128,145,155,.14)}
div[data-baseweb="tab-list"] {gap:.8rem}
div[data-baseweb="tab"] {font-weight:580}
</style>''',unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def read_csv(path, stamp):
    if not path.exists(): return pd.DataFrame()
    try: return pd.read_csv(path,encoding='utf-8-sig',keep_default_na=True)
    except (OSError,pd.errors.EmptyDataError): return pd.DataFrame()

def load(name):
    p=OUT/name
    return read_csv(p,p.stat().st_mtime_ns if p.exists() else None)

# Positional metrics are descriptive, not part of the Form calculation.
POSITION_METRICS={
    'Strikers':['goals','xg','shots','shots_on_target','touches_box','chances','aerials_won'],
    'Wingers':['assists','xa','chances','dribbles','touches_box','crosses','shots'],
    'Midfielders':['chances','xa','final_third_passes','line_breaking_passes','recoveries','tackles','interceptions'],
    'Defenders':['clearances','interceptions','tackles','aerials_won','ground_duels_won','shot_blocks','recoveries'],
    'Goalkeepers':['saves','goals_prevented','goals_conceded','high_claims'],
}
METRIC_LABELS={'xg':'Expected goals (xG)','xa':'Expected assists (xA)','touches_box':'Touches in box',
    'final_third_passes':'Passes into final third','line_breaking_passes':'Line-breaking passes',
    'shots_on_target':'Shots on target','aerials_won':'Aerial duels won','ground_duels_won':'Ground duels won',
    'shot_blocks':'Blocked shots','high_claims':'High claims','goals_prevented':'Goals prevented'}

def metric_name(key):return METRIC_LABELS.get(key,key.replace('_',' ').capitalize())

def metrics_for(group):return POSITION_METRICS.get(group,POSITION_METRICS['Midfielders'])

def profile_row(name):
    data=load('player_details.csv')
    if data.empty or 'player' not in data:return None
    found=data[data['player']==name]
    return found.iloc[0] if len(found) else None

def profile_table(profile,metrics,per90):
    rows=[]
    for key in metrics:
        suffix='per90' if per90 else 'total'
        value=profile.get(f'{key}_{suffix}')
        if pd.isna(value): continue
        mins=profile.get(f'{key}_rated_minutes')
        games=profile.get(f'{key}_games')
        complete=profile.get(f'{key}_complete')=='yes'
        rows.append({'Metric':metric_name(key),'Value':round(float(value),2),
                     'Coverage':f'{int(games)} matches · {int(mins)} mins'+('' if complete else ' · partial')})
    return pd.DataFrame(rows)

def number(v, decimals=1):
    try:
        if pd.isna(v): return '—'
        return f'{float(v):,.{decimals}f}'
    except (TypeError,ValueError): return '—'

def cell_color(value, kind):
    if pd.isna(value):return 'color: #8f99a4;'
    try: n=float(value)
    except (TypeError,ValueError):return ''
    if kind=='league':
        tint='#d7f3e8' if n>=.9 else '#e2edf9' if n>=.8 else '#fff1d7' if n>=.7 else '#f0e7ee'
        ink='#115c47' if n>=.9 else '#23527b' if n>=.8 else '#8a5a11' if n>=.7 else '#75465a'
    elif kind=='rating':
        tint='#d5f1e5' if n>=7.5 else '#e4f3ed' if n>=7.0 else '#f9efd6' if n>=6.5 else '#fae4e2'
        ink='#12644d' if n>=7.0 else '#855c16' if n>=6.5 else '#933f3b'
    else:
        tint='#d5f1e5' if n>=70 else '#e2edf9' if n>=58 else '#f9efd6' if n>=45 else '#f5e2e5'
        ink='#12644d' if n>=70 else '#275581' if n>=58 else '#855c16' if n>=45 else '#883f53'
    return f'background-color:{tint};color:{ink};font-weight:650;'

def style_table(frame):
    frame=frame.replace(['None','none','nan','NaN',''],pd.NA)
    styler=frame.style.format(na_rep='—')
    colors={'League strength':'league','Rating':'rating','Form':'form','Performance':'form'}
    for col,kind in colors.items():
        if col in frame.columns:
            # pandas 1.x and 2.x compatibility
            fun=lambda v, k=kind: cell_color(v,k)
            styler=styler.map(fun,subset=[col]) if hasattr(styler,'map') else styler.applymap(fun,subset=[col])
    return styler

board=load('leaderboard.csv')
if board.empty:
    st.error('No output/leaderboard.csv found. Run the tracker, then reopen this dashboard.')
    st.stop()
for c in ['minutes','minutes_pct','form_index','avg_rating','weighted_rating','performance_score','coefficient','goals','assists','games_played','window_games','chances','recoveries','interceptions','clearances','duels_won']:
    if c in board:board[c]=pd.to_numeric(board[c],errors='coerce')
for c in ['player','club','league','position_group','position','status','identity_status']:
    if c not in board:board[c]=''
    board[c]=board[c].fillna('').astype(str)
# Missing numeric entries remain missing, never literal None or a fabricated strength.
board['is_complete']=board['status'].isin(['OK','OK_SEASON_TO_DATE'])
board['is_scored']=board['form_index'].notna()
# Asterisk indicates potential dual-national / international-allegiance consideration, not confirmed Welsh eligibility.
STAR_NAMES={'Ashley Phillips','Mikey Moore','Rhodri Smith'}
board['display_name']=board['player'].map(lambda v: v+'*' if v in STAR_NAMES else v)

def readable_status(row):
    """Human descriptions: no provider rating is not the same as no minutes."""
    raw=str(row.get('status',''))
    if row.get('identity_status')!='verified_manual' or raw=='IDENTITY_PENDING_REVIEW': return 'Identity pending'
    if raw=='NO_LEAGUE_WEIGHT':return 'League not rated'
    if raw=='NO_FIXTURES':return 'Fixtures unavailable'
    if raw=='INCOMPLETE_DATA':return 'Incomplete match data'
    if raw=='NO_RATINGS':
        return 'Rating unavailable' if (row.get('games_played') or 0)>0 else 'No rated appearances'
    if raw=='PARTIAL_RATINGS':return 'Partial ratings'
    if raw=='LOW_MINUTES':return 'Limited minutes'
    if raw=='ESTIMATED_MINUTES':return 'Estimated minutes'
    if raw=='OK_SEASON_TO_DATE':return 'Season to date'
    if raw=='OK':return 'Complete'
    return raw.replace('_',' ').capitalize()

board['coverage_label']=board.apply(readable_status,axis=1)


st.title('Cymru Form Tracker')
st.markdown('Cymry player rankings, using match ratings and minutes played in each club’s last 10 completed league fixtures.')
st.caption('*Match ratings and statistics: PitchAPI unless otherwise stated. External-source figures are labelled individually.*')
from datetime import datetime, timezone
updated_file=OUT/'updated_at.txt'
if updated_file.exists():
    updated_text=updated_file.read_text(encoding='utf-8').strip()
else:
    updated_text=datetime.fromtimestamp((OUT/'leaderboard.csv').stat().st_mtime,timezone.utc).strftime('%d %b %Y · %H:%M UTC')
st.caption('Data updated: '+updated_text)
with st.sidebar:
    st.markdown('### Explore')
    leagues=sorted(x for x in board['league'].unique() if x)
    chosen_leagues=st.multiselect('Leagues',leagues,default=[],placeholder='All leagues',help='Leave empty to include all leagues. Select one or more to narrow the ranking.')
    positions=sorted(x for x in board['position_group'].unique() if x)
    chosen_positions=st.multiselect('Positions',positions,default=[],placeholder='All positions',help='Leave empty to include all positions. Select one or more to narrow the ranking.')
    scope=st.radio('Coverage',['All rated players','Everyone'],index=0)
    squad=st.checkbox('November Wales squad only')
    query=st.text_input('Player or club',placeholder='Search').strip()
    st.divider()
    st.caption('Model weights: PL 1.00 · Bundesliga 0.90 · Championship/Belgium 0.80 · Scottish PL/2. Bundesliga/MLS/Norway/Poland/Czechia 0.75 · L1 0.70 · A-League 0.65 · L2 0.60. These are independent model choices.')
    st.caption('Only approved identities can receive form scores. Unrated players remain visible in the Player and Data quality tabs.')

filtered=board.copy()
if chosen_leagues: filtered=filtered[filtered['league'].isin(chosen_leagues)]
if chosen_positions: filtered=filtered[filtered['position_group'].isin(chosen_positions)]
if scope=='All rated players':filtered=filtered[filtered['is_scored']]
if squad and 'selected_nov_2026' in filtered:
    filtered=filtered[filtered['selected_nov_2026'].astype(str).str.lower().isin(['yes','true','1'])]
if query:filtered=filtered[filtered['player'].str.contains(query,case=False,regex=False)|filtered['club'].str.contains(query,case=False,regex=False)]

c1,c2,c3,c4=st.columns(4)
c1.metric('Tracked',len(board),help='Active players in the tracking database, including those without a form score.')
c2.metric('Rated',int(board['is_scored'].sum()),help='Players with an approved identity and enough recorded match data to calculate a form score. Includes provisional scores.')
c3.metric('Verified windows',int((board['is_scored']&board['is_complete']).sum()),help='Players with complete or complete season-to-date fixture windows and a form score. Excludes provisional or limited-data windows.')
c4.metric('Pending / no score',int((~board['is_scored']).sum()),help='Players without a form score, including unverified identities, missing match ratings and uncovered competitions. Not necessarily zero-minute players.')
st.markdown('''<div style="display:flex;gap:15px;align-items:center;flex-wrap:wrap;margin:.85rem 0 .65rem;font-size:.77rem;opacity:.85">
<span><b style="color:#22936e">●</b> Strong</span><span><b style="color:#447bb3">●</b> Competitive</span><span><b style="color:#c29432">●</b> Lower / developing</span><span style="opacity:.7">Colour thresholds vary by metric</span></div>''',unsafe_allow_html=True)

# A stateful view selector allows a clicked leaderboard row to open a Player profile.
# Streamlit tabs do not support programmatic navigation.
if st.session_state.get('active_view') not in ('Leaderboard','Player','Compare','Data quality'):
    st.session_state['active_view']='Leaderboard'
st.radio('View', ['Leaderboard','Player','Compare','Data quality'], horizontal=True,
         key='active_view', label_visibility='collapsed')
if st.session_state['active_view']=='Leaderboard':
    ranking={'Form index':'form_index','Performance quality':'performance_score','Average rating':'avg_rating','Minutes %':'minutes_pct','Goals':'goals','Assists':'assists'}
    metric=st.selectbox('Sort by',list(ranking),label_visibility='collapsed',help='Reorders the table by the selected measure. The Form index combines match quality, league strength and playing time.')
    key=ranking[metric]
    if key not in filtered:st.info('This metric is not available in the current CSV.')
    else:
        table=filtered.sort_values([key,'player'],ascending=[False,True],na_position='last').copy()
        table.insert(0,'#',range(1,len(table)+1))
        shown={'#':'#','display_name':'Player','club':'Club','league':'League','coefficient':'League strength','position':'Position',
               'minutes_pct':'Minutes %','avg_rating':'Rating','performance_score':'Performance','form_index':'Form',
               'goals':'G','assists':'A','coverage_label':'Coverage'}
        cols=[k for k in shown if k in table.columns]
        display=table[cols].rename(columns=shown)
        config={
            '#': st.column_config.NumberColumn('#',help='Rank within your current filters and chosen sorting metric.'),
            'Player': st.column_config.TextColumn('Player',help='Tracked player. * marks a potential dual-national or international-allegiance consideration, not confirmed eligibility.'),
            'Club': st.column_config.TextColumn('Club',help='Current playing club used for the recent-fixture window.'),
            'League': st.column_config.TextColumn('League',help='Domestic league used for the club’s recent matches; cups are excluded.'),
            'League strength': st.column_config.NumberColumn('League strength',format='%.2f',help='Our independently assigned league difficulty multiplier: Premier League 1.00, Championship 0.80, etc. Not an official Opta coefficient.'),
            'Position': st.column_config.TextColumn('Position',help='Primary and secondary positions from the player list. The first position determines their position group.'),
            'Minutes %': st.column_config.ProgressColumn('Minutes %',min_value=0,max_value=100,format='%.1f%%',help='Minutes played ÷ (90 × completed club league fixtures in the available window). Missing-match data is not treated as zero minutes.'),
            'Rating': st.column_config.NumberColumn('Rating',format='%.2f',help='Arithmetic mean of available PitchAPI match ratings (0–10). Matches without a provider rating are excluded.'),
            'Performance': st.column_config.NumberColumn('Performance',format='%.1f',help='Minutes-weighted average match rating × 10 × league strength. Measures rated-match quality before the playing-time adjustment.'),
            'Form': st.column_config.NumberColumn('Form',format='%.1f',help='Performance × (0.5 + 0.5 × minutes share, capped at 100%). The principal ranking score.'),
            'G': st.column_config.NumberColumn('G',format='%d',help='Goals recorded in the club’s recent league-fixture window.'),
            'A': st.column_config.NumberColumn('A',format='%d',help='Assists recorded in the club’s recent league-fixture window.'),
            'Coverage': st.column_config.TextColumn('Coverage',help='Data completeness: Complete, Season to date, Partial ratings, Limited minutes, Rating unavailable, Identity pending, etc.')
        }
        for integer_col in ('G','A'):
            if integer_col in display.columns: display[integer_col]=pd.to_numeric(display[integer_col],errors='coerce').astype('Int64')
        # Selection is captured in a callback before the next script rerun. This
        # safely updates the view and the Player dropdown without injected JS.
        def open_selected_player():
            widget=st.session_state.get('leaderboard_selection', {})
            selected=widget.get('selection', {}).get('rows', [])
            if selected and 0 <= selected[0] < len(table):
                st.session_state['player_choice']=str(table.iloc[selected[0]]['player'])
                st.session_state['active_view']='Player'
        st.caption('Select a player’s name or row to open their profile.')
        st.dataframe(style_table(display),hide_index=True,use_container_width=True,height=610,
                     column_config=config,key='leaderboard_selection',
                     on_select=open_selected_player,selection_mode='single-row')
        st.caption('Coverage: **Rating unavailable** means minutes were recorded without provider ratings; **No rated appearances** means no rated match was found (not proof of zero playing time). Partial ratings are provisional.')
        st.download_button('Export selection',table.to_csv(index=False).encode('utf-8-sig'),file_name='welsh_form_selection.csv',mime='text/csv')
        with st.expander('How are the numbers calculated?'):
            st.markdown('''**Rating** — average provider match rating (out of 10) for rated appearances; **League strength** — our subjective league coefficient (Premier League = 1.00). **Performance** — minutes-weighted match rating × 10 × strength. **Minutes %** — minutes played divided by 90 × number of club league fixtures in the available window. **Form** — Performance × (0.5 + 0.5 × Minutes % / 100). **G / A** — whole-number goals and assists. A 9-game complete season-to-date sample is labelled as such rather than treated as an error. Current window covers *league fixtures only*; cups are not yet included.''')
        st.caption('* Potential dual-national / allegiance-switch interest; not a statement of confirmed eligibility. The ranking uses PitchAPI club-league statistics only.')
if st.session_state['active_view']=='Player':
    player_options=board.copy()
    if chosen_leagues: player_options=player_options[player_options['league'].isin(chosen_leagues)]
    if chosen_positions: player_options=player_options[player_options['position_group'].isin(chosen_positions)]
    if squad and 'selected_nov_2026' in player_options:
        player_options=player_options[player_options['selected_nov_2026'].astype(str).str.lower().isin(['yes','true','1'])]
    if query:player_options=player_options[player_options['player'].str.contains(query,case=False,regex=False)|player_options['club'].str.contains(query,case=False,regex=False)]
    names=sorted(player_options['player'].unique().tolist())
    if not names:st.info('No players match these filters.')
    else:
        if st.session_state.get('player_choice') not in names:
            st.session_state['player_choice']=names[0]
        choice=st.selectbox('Player',names,key='player_choice')
        p=player_options[player_options['player']==choice].iloc[0]
        st.subheader(p['display_name'])
        st.caption(f"{p['club']} · {p['league']} · {p['position_group']} ({p['position']}) · {p['coverage_label']}")
        a,b,c,d=st.columns(4)
        a.metric('Form score',number(p.get('form_index')))
        b.metric('Match rating',number(p.get('avg_rating'),2))
        c.metric('League strength',number(p.get('coefficient'),2))
        d.metric('Minutes played',number(p.get('minutes'),0))
        extras=['minutes_pct','performance_score','games_played','window_games','goals','assists','chances','recoveries','interceptions','clearances','duels_won']
        details=[]
        for k in extras:
            val=p.get(k,'—')
            if k in ('goals','assists') and pd.notna(val):
                try: val=int(float(val))
                except (ValueError,TypeError): pass
            details.append({'Statistic':k.replace('_',' ').title(),'Value':val})
        st.dataframe(pd.DataFrame(details),hide_index=True,use_container_width=True)
        logs=load('match_logs.csv')
        if logs.empty: logs=load('match_trends.csv')  # public export contains compact fixture trends
        if not logs.empty and 'player' in logs:
            log=logs[logs['player']==choice]
            if 'date' in log:log=log.sort_values('date',ascending=False)
            st.markdown('**Recent fixtures**')
            # The trend excludes missing ratings rather than drawing invented zeroes.
            chart_rows=log.copy()
            for c in ('rating','minutes'):
                if c in chart_rows:chart_rows[c]=pd.to_numeric(chart_rows[c],errors='coerce')
            st.markdown('**Match-by-match form**')
            rated=chart_rows.dropna(subset=['rating']) if 'rating' in chart_rows else pd.DataFrame()
            if not rated.empty:
                rated=rated.sort_values('date')
                st.line_chart(rated.set_index('date')['rating'])
                st.caption(f'{len(rated)} rated fixtures shown. Gaps in the provider feed are excluded, not scored as zero.')
            else:st.caption('No individual match ratings available for this player.')
            if 'minutes' in chart_rows and chart_rows['minutes'].notna().any():
                st.bar_chart(chart_rows.sort_values('date').set_index('date')['minutes'])
            visible=[x for x in ['date','opponent','home_away','minutes','rating','goals','assists','status'] if x in chart_rows]
            st.dataframe(chart_rows[visible],hide_index=True,use_container_width=True)
        with st.expander('Detailed stats · position profile',expanded=True):
            prof=profile_row(choice)
            if prof is None:
                st.info('Detailed metrics will appear after the next tracker refresh. Unverified players are not assigned a statistical profile.')
            else:
                per90=st.toggle('Per 90 minutes',value=True,key='player_per90',help='Each per-90 figure uses only minutes in matches where that particular statistic was provided. Partial coverage is clearly marked.')
                stats=profile_table(prof,metrics_for(p['position_group']),per90)
                if len(stats):st.dataframe(stats,hide_index=True,use_container_width=True,column_config={'Value':st.column_config.NumberColumn('Per 90' if per90 else 'Total',format='%.2f')})
                else:st.info('No position-specific statistics available from the provider in this window.')
                mins=float(prof.get('minutes_recorded') or 0)
                if mins<270:st.caption(f'Limited sample: {mins:.0f} recorded minutes. Per-90 rates may be volatile.')
                st.caption('Missing provider fields are omitted, not counted as zero. “Partial” means the statistic was provided for fewer than all recorded appearances. These metrics do not affect the Form score.')
if st.session_state['active_view']=='Compare':
    if len(filtered)<2:st.info('Select at least two players using the sidebar filters.')
    else:
        default=filtered.sort_values('form_index',ascending=False)['player'].head(2).tolist()
        choices=st.multiselect('Compare players',sorted(filtered['player'].unique()),default=default,max_selections=5)
        if choices:
            rows=filtered[filtered['player'].isin(choices)].set_index('player')
            show=[c for c in ['club','league','coefficient','status','minutes_pct','avg_rating','performance_score','form_index','goals','assists','chances','recoveries','interceptions','duels_won'] if c in rows]
            st.dataframe(rows[show].T,use_container_width=True)
            chart=rows[['form_index']].dropna()
            if not chart.empty:st.bar_chart(chart,horizontal=True,color='#278f86')
            st.markdown('**Position-specific comparison**')
            groups=rows['position_group'].dropna().unique().tolist() if 'position_group' in rows else []
            if len(groups)>1:st.caption('Different positions selected: metrics may describe different roles and are not adjusted for league strength.')
            position=st.selectbox('Statistical profile', ['Attack','Creation','Progression','Defending','Goalkeeping'],key='comparison_profile')
            comparison_sets={
                'Attack':['goals','xg','shots','shots_on_target','touches_box'],
                'Creation':['assists','xa','chances','crosses','dribbles'],
                'Progression':['final_third_passes','line_breaking_passes','long_balls','recoveries'],
                'Defending':['tackles','interceptions','clearances','aerials_won','ground_duels_won'],
                'Goalkeeping':['saves','goals_prevented','goals_conceded','high_claims']}
            per90=st.toggle('Compare per 90 minutes',value=True,key='compare_per90')
            prof=load('player_details.csv')
            if prof.empty:st.info('Run REFRESH.cmd to generate detailed player profiles.')
            else:
                subset=prof[prof['player'].isin(choices)]
                suffix='per90' if per90 else 'total'
                comparisons=[]
                for metric_name_key in comparison_sets[position]:
                    col=f'{metric_name_key}_{suffix}'
                    if col not in subset:continue
                    for _,person in subset.iterrows():
                        val=pd.to_numeric(person.get(col),errors='coerce')
                        if pd.isna(val):continue
                        if float(person.get('minutes_recorded') or 0)<180:continue
                        coverage='Partial' if person.get(f'{metric_name_key}_complete')!='yes' else 'Full'
                        comparisons.append({'Metric':metric_name(metric_name_key),'Player':person['player'],'Value':round(float(val),2),'Coverage':coverage})
                if comparisons:
                    comparison=pd.DataFrame(comparisons)
                    st.dataframe(comparison.pivot(index='Metric',columns='Player',values='Value'),use_container_width=True)
                    st.caption('Players under 180 recorded minutes are excluded from detailed comparison. Missing metrics remain blank. Per-90 figures use only matches reporting each statistic; see Player profiles for coverage.')
                else:st.info('No comparable statistics with sufficient minutes in this category.')
if st.session_state['active_view']=='Data quality':
    status=board.groupby('coverage_label',dropna=False).size().sort_values(ascending=False).rename('Players').reset_index().rename(columns={'coverage_label':'Coverage'})
    st.markdown('**Coverage by status**')
    st.dataframe(status,hide_index=True,use_container_width=True)
    cov=load('coverage.csv')
    if not cov.empty:
        st.markdown('**League coverage**')
        st.dataframe(cov,hide_index=True,use_container_width=True)
    registry=BASE/'player_registry.csv' if not PUBLIC_MODE else Path('/no_private_registry.csv')
    if registry.exists():
        reg=read_csv(registry,registry.stat().st_mtime_ns)
        if not reg.empty and 'identity_status' in reg:
            pending=reg[reg['identity_status'].astype(str)!='verified_manual']
            st.markdown(f'**Identity approval queue · {len(pending)} players**')
            cols=[c for c in ['player','club','league','identity_status','club_status'] if c in pending]
            st.dataframe(pending[cols],hide_index=True,use_container_width=True,height=240)
    issues=load('issues.csv') if not PUBLIC_MODE else pd.DataFrame()
    if not issues.empty:
        st.markdown('**Collection issues**')
        st.caption(f'{len(issues)} issue records (not necessarily {len(issues)} separate player failures).')
        st.dataframe(issues,hide_index=True,use_container_width=True,height=320)
    st.info('Blank scores mean missing or unapproved ratings, not zero performance. Matches are domestic league fixtures only.')
