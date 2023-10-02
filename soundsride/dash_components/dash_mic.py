import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash_html_components.Div import Div
import numpy as np
from numpy.core.numeric import full
import plotly.graph_objects as go

from dash.dependencies import Input, Output

from .mic import Mic

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div(
    html.Div([
        html.H4('Silence Detector'),
        html.Div([
           html.Button("Start Recording", id="start-recording-button"),
           html.Button("Stop Recording", id="stop-recording-button"),
           html.Button("Play", id="play-button")
        ]),
        html.Div(id='live-update-text'),
        dcc.Graph(id='live-update-graph'),
        dcc.Interval(
            id='interval-component',
            interval=1*500, # in milliseconds
            n_intervals=0
        )
    ])
)

class State: 
    pass


class RecordingState(State): 
    def __init__(self):
        self.mic = Mic()
        self.chunks = list()
        self.chunks_displayed = 0
        self.samples_displayed = 0

        self.stream, n_channels, samplerate = self.mic.get_recording_stream(self.chunks)
        self.stream.start()

        self.fig = go.Figure()

    def update_fig(self):
        n_new_chunks = len(self.chunks) - (self.chunks_displayed)
        
        if n_new_chunks == 0:
            return
        
        channel = 0
        subsample_rate = 100

        new_batch = self.chunks[
                (self.chunks_displayed):
                (self.chunks_displayed+n_new_chunks)]
        
        new_recording = np.vstack(new_batch)

        new_recording = new_recording[::subsample_rate,channel]

        self.fig.add_trace(
            go.Scatter(
                x=np.arange(self.samples_displayed, self.samples_displayed + len(new_recording)),
                y=new_recording
            )
        )

        self.chunks_displayed += n_new_chunks
        self.samples_displayed += len(new_recording)

    def stop_recording(self) -> "IdleState":
        pass

class IdleState(State): 
    def __init__(self):
        pass

    def start_recording(self) -> "RecordingState":
        return RecordingState()

    def play(self) -> "PlayingState":
        pass

class PlayingState(State):
    def wait(self) -> "IdleState":
        pass


class Controller():
    def __init__(self) -> None:
        self.state = IdleState()


controller = Controller()

@app.callback(Output('live-update-text', 'children'),
            Input('interval-component', 'n_intervals'))
def update_clock(n: int):
    # style = {'padding': '5px', 'fontSize': '16px'}
    return [
        "Datetime ", 
        datetime.datetime.now(), 
        " Length ",
        len(controller.chunks)
    ]


@app.callback(Output('live-update-graph', 'figure'),
            Input('interval-component', 'n_intervals'))
def update_graph_live(n):
    controller.update_fig()
    return controller.fig





if __name__ == '__main__':
    app.run_server(debug=True)