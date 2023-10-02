import json
from pathlib import Path

import dash
from dash.exceptions import PreventUpdate
import dash_html_components as html
from dash.dependencies import Input, Output, State, ALL

from .dash_mix import DashTransitionControl
from .dash_player import DashPlayer
from .dash_mix_plan import DashMixPlan

from .mix_plan import TransitionSpec, MixPlan, MixPlanViz
from .song import Song

datafiles = Path("./tests/data/")

def load_song() -> Song:
    audio_file = Path(datafiles / "tsunami.mp3")
    metadata_file = Path(datafiles / "tsunami.txt")

    song = Song(audio_file, metadata_file)
    print(song.transition_table)
    return song

song = load_song()

# Dash App
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

dash_transition_control = DashTransitionControl(list(song.transition_table.keys()))
dash_mix_plan = DashMixPlan()
dash_player = DashPlayer()

_app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
_app.layout = html.Div([
    dash_transition_control.get_component(),
    dash_mix_plan.get_component(),
    dash_player.get_component()
])

# Callbacks

def schedule_mix_plan(transition_spec: TransitionSpec, song: Song) -> MixPlan:
    mix_plan = MixPlan()

    genre_transitions = transition_spec.genre_transitions.copy()
    left_genre = genre_transitions[0]
    del genre_transitions[0]


    for timestamp, right_genre in genre_transitions.items():
        print("from ", left_genre, " to ", right_genre)
        mix_plan.add_snippet_transition(
            song.get_full_snippets_by_genres(left_genre, right_genre).pop(),
            timestamp)
        
        left_genre = right_genre

    return mix_plan   
    

def get_transition_spec_from_ui_state(toggles, dd_tos, sliders):
    toggles = [True] + toggles
    sliders = [0] + sliders

    genre_transitions = dict()
    for toggle, dd_to, slider in zip(toggles, dd_tos, sliders):
        if toggle:
            genre_transitions[slider * 1000] = dd_to

    return TransitionSpec(genre_transitions)


current_mix_plan = None
mix_plan_fig = None
updating = False

@_app.callback(
    Output("interval-playback", "disabled"),
    Output("graph-playback", "figure"),
    Output("div-timecode", "children"),
    Output("graph-mix-plan", "figure"),
    Input({"type": "toggle", "index": ALL}, "on"),
    Input({"type": "dd-to", "index": ALL}, "value"),
    Input({"type": "slider", "index": ALL}, "value"),
    Input("button-play", "n_clicks"),
    Input("interval-playback", "n_intervals"),
    prevent_initial_call=True
)
def playback_current_mix_plan(toggles, dd_tos, sliders, n_clicks: int, n_intervals: int):
    trigger = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        
    global current_mix_plan
    global mix_plan_fig 
    global updating

    if updating:
        raise PreventUpdate()

    updating = True
    
    if trigger.startswith("{"):
        print("trigger starts with {", trigger, flush=True)
        trigger = json.loads(trigger)
        if trigger["type"] in ["toggle", "slider", "dd-to"]:    
            print(trigger, flush=True)
            transition_spec = get_transition_spec_from_ui_state(toggles, dd_tos, sliders)
            current_mix_plan = schedule_mix_plan(transition_spec, song)
            current_mix_plan.set_snippet_transitions(transition_type="crossfade")
            current_mix_plan.print_to_console()
            mix_plan_viz = MixPlanViz()        
            mix_plan_viz.viz_transition_spec(transition_spec)
            mix_plan_viz.viz_mix_plan(current_mix_plan)
            mix_plan_fig = mix_plan_viz.get_fig()
            
            if dash_player.is_playing():
                segment = current_mix_plan.to_audio_segment()
                dash_player.swap_segment(segment)
            
            updating = False
            return True, dash_player._fig, "tbd", mix_plan_fig

    if trigger == "button-play" and n_clicks:
        if dash_player.is_playing():
            dash_player.stop()
            
            updating = False
            return False, None, "tbd", mix_plan_fig
        else:
            segment = current_mix_plan.to_audio_segment()
            dash_player.play(segment)
            
            updating = False
            return False, dash_player._fig, "tbd", mix_plan_fig
        
    if trigger == "interval-playback" and n_intervals:
        sample_position = dash_player._playback_state.played_milliseconds    
        dash_player._set_marker(sample_position)

        updating = False
        return dash_player._playback_state.playback_future.done(), dash_player._fig, sample_position, mix_plan_fig




_app.run_server(debug=True)