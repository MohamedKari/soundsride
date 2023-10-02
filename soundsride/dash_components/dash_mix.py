import json
from typing import Callable, List

import dash
import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Input, Output, State, ALL
from dash_html_components.Div import Div

from .mix_plan import TransitionSpec

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

class DashTransitionControl:
    def __init__(self, genres: List[str]) -> None:
        self._end_ts = 300
        self._marks_interval = 30

        self._slider_marks = dict(zip(
            range(0, self._end_ts, self._marks_interval), 
            [{"label": str(mark) } for mark in range(0, self._end_ts, self._marks_interval)]))

        self._dd_options = [
            dict([("label", genre), ("value", genre)]) for genre in genres
        ]

    def _create_initial_tranistion_control(self) -> html.Div:
        return html.Div(id=f"transition-control-0", children=[
                html.Div("", style={"width": "8%", "display": "inline-block"}),
                html.Div(
                    dcc.Dropdown(
                        id={"type": "dd-to", "index": 0},
                        options=self._dd_options,
                        value=self._dd_options[0]["value"]),
                    style={
                        "width": "20%",
                        "display": "inline-block"
                    }
                ),
                html.Div("", style={"width": "70%", "display": "inline-block"}),
            ])


    def _create_single_transition_control(self, i: int) -> html.Div:
        return html.Div(id=f"transition-control-{i}", children=[
                html.Div(
                    daq.BooleanSwitch(
                        id={"type": "toggle", "index": i},
                        on=False
                    ),
                    style={
                        "width": "8%",
                        "display": "inline-block"
                    }
                ),
                html.Div(
                    dcc.Dropdown(
                        id={"type": "dd-to", "index": i},
                        options=self._dd_options,
                        value=self._dd_options[0]["value"]),
                    style={
                        "width": "20%",
                        "display": "inline-block"
                    }
                ), 
                html.Div(
                    dcc.Slider(
                        id={"type": "slider", "index": i},
                        min=0,
                        max=self._end_ts,
                        step=1,
                        value=self._end_ts / 2,
                        marks=self._slider_marks
                    ),
                    style={
                        "width": "70%",
                        "display": "inline-block"
                    }
                )      
            ])

    def _create_transition_spec_description_container(self) -> html.Div:
        return html.Div(
                    "<tbd>",
                    id="div-spec-description"
        )

    def get_component(self) -> html.Div:
        return html.Div(
            html.Div([
                self._create_initial_tranistion_control(),
                self._create_single_transition_control(1),
                self._create_single_transition_control(2),
                self._create_single_transition_control(3),
                self._create_single_transition_control(4),
                self._create_transition_spec_description_container()
            ])
        )

    def register_callbacks(self, app: dash.Dash):
        def update_spec_description(n_clicks, toggles, dd_tos, sliders):
            toggles = [True] + toggles
            sliders = [0] + sliders

            genre_transitions = dict()
            for toggle, dd_to, slider in zip(toggles, dd_tos, sliders):
                if toggle:
                    genre_transitions[slider] = dd_to

            serialized_genre_transitions = json.dumps(genre_transitions, indent=4)

            return serialized_genre_transitions

        app.callback(
            Output("div-spec-description", "children"),
            Input("button-update-spec", "n_clicks"), 
            State({"type": "toggle", "index": ALL}, "on"),
            State({"type": "dd-to", "index": ALL}, "value"),
            State({"type": "slider", "index": ALL}, "value")
        )(update_spec_description)

if __name__ == "__main__":
    external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

    dsah_transition_control = DashTransitionControl()

    app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
    app.layout = html.Div(
        dsah_transition_control.get_component()
    )

    dsah_transition_control.register_callbacks(app)

    app.run_server(debug=True)