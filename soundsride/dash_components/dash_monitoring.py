from inspect import ArgSpec
from os import sendfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import logging

import dash
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, ALL


from .dash_player import DashPlayer
from .dash_mix_plan import DashMixPlan

from .mix_plan import TransitionSpec, MixPlan, MixPlanViz

from .session import AppModel
from .service.server import GrpcServer

from . import log
log.setup_logger(module_exclusions=["werkzeug"])

# Dash App
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

dash_mix_plan = DashMixPlan()
dash_player = DashPlayer()

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div([
    html.Div("<tbd>", id="current-counter"),
    dash_mix_plan.get_component(),
    dash_player.get_component(),
    dcc.Interval(
        id='interval-eventloop',
        disabled=False,
        interval=5000, # ms
        n_intervals=0
    )
])

# Callbacks

app_model = AppModel()

@app.callback(
    Output("current-counter", "children"),
    # Output("div-timecode", "children"),
    # Output("graph-playback", "figure"),
    Output("graph-mix-plan", "figure"),
    Input("interval-eventloop", "n_intervals"),
    prevent_initial_call=True
)
def playback_current_mix_plan(n_intervals: int):
    trigger = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    print("CALLBACK:", app_model.mix_plan_fig)
    return repr(app_model.transition_spec), app_model.mix_plan_fig


    if app_model.updated_model:
        app_model.updated_model = False
        if dash_player.is_playing():
            dash_player.swap_segment(app_model.segment)
        else:
            dash_player.play(app_model.segment)

    if dash_player.is_playing():
        app_model.sample_position = dash_player._playback_state.played_milliseconds    
        dash_player._set_marker(app_model.sample_position)


    # return repr(app_model.transition_spec), sample_position, dash_player._fig, mix_plan_fig
    return repr(app_model.transition_spec)# , app_model.sample_position, dash_player._fig, 



if __name__ == "__main__":
    grpc_server = GrpcServer(app_model=app_model)
    grpc_server.start_daemon()

    # WARNING: We must disable debugging, in particular hot-reloading, to make sure that singleton objects such as the AppModel are only instantiated once
    app.run_server(debug=False)