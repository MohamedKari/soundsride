import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from pydub import AudioSegment
import numpy as np
import scipy.signal as sps

from .player import Player

class DashPlayer:
    def __init__(self):
        self._fig: go.Figure = go.Figure()
        
        self._player = None
        self._playback_state = None
        self._marker_y = None

    def get_component(self) -> html.Div:
        return html.Div([
            html.Button(
                "Play",
                id="button-play"
            ),
            html.Div(
                "tbd",
                id="div-timecode"
            ),
            dcc.Graph(id="graph-playback"),
            dcc.Interval(
                id='interval-playback',
                disabled=True,
                interval=400, # ms
                n_intervals=0
            )
        ])

    def _set_marker(self, x):
        # Unset marker
        self._fig["layout"]["shapes"] = list()

        self._fig.add_shape(
            type="line",
            x0=x, y0=-1 * self._marker_y, x1=x, y1=self._marker_y,
            line={
                "color": "red",
                "width": 3
            })

    def is_playing(self):
        return self._playback_state and self._playback_state.state == "running"

    def _update_playback_figure(self, segment: AudioSegment):
        n_channels = segment.channels
        subsample_rate = 3000
        raw_samples = segment.get_array_of_samples()
        raw_samples = np.array(raw_samples)
        
        # TODO: Average all channels
        raw_samples = raw_samples[::n_channels]
        
        subsampled = sps.resample(raw_samples, len(raw_samples) // subsample_rate)
        sample_rate_after_subsampling = len(subsampled) / (len(raw_samples) / segment.frame_rate)

        idx = np.arange(len(subsampled)) / sample_rate_after_subsampling * 1000

        self._fig.add_trace(go.Scatter(x=idx, y=subsampled))

        self._marker_y = np.abs(np.max(subsampled))

        self._fig.update_yaxes(range=[-1 * self._marker_y, self._marker_y])
        self._fig.update_xaxes(range=[0, len(subsampled) / sample_rate_after_subsampling * 1000])

    def play(self, segment: AudioSegment):
        self._player = Player(segment)
        self._playback_state = self._player.play_stream()
        
        self._update_playback_figure(segment)

    def stop(self):
        self._playback_state.request_stop = True
        self._fig["data"] = tuple()

    def swap_segment(self, segment: AudioSegment):
        self._playback_state.swap_segment = segment
        
        self._fig["data"] = tuple()
        self._update_playback_figure(segment)