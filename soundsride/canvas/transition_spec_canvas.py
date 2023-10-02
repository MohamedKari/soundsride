import pathlib
from soundsride.consolidator import UpdatingStrategy
from typing import Deque, Tuple, List
from collections import deque
import logging
import time
from pathlib import Path
from fire import Fire

from PIL import Image, ImageColor
import numpy as np

import pydub
import torch
import torchaudio
from pydub import AudioSegment

import matplotlib as mpl
from matplotlib.gridspec import GridSpec
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.figure as mplfigure

from ..mix_plan import TransitionSpec, ScheduledSnippet

logging.getLogger("matplotlib").setLevel(logging.WARNING)

class TransitionCanvas():
    def __init__(self, absolute_time_origin_in_ms: int = 0, absolute_time_horizon_in_ms: int = 0, waveform_time_offset_in_ms: int = 0) -> None:
        self.width, self.height = 2000, 3000
        self.fig = mplfigure.Figure(frameon=False)

        self.dpi = self.fig.get_dpi()
        
        # add a small 1e-2 to avoid precision lost due to matplotlib's truncation
        # (https://github.com/matplotlib/matplotlib/issues/15363)
        self.fig.set_size_inches(
            (self.width + 1e-2) / self.dpi,
            (self.height + 1e-2) / self.dpi)

        self.canvas = FigureCanvasAgg(self.fig)

        self.grid_spec = GridSpec(
            4, 1, 
            figure=self.fig,
            height_ratios=[.4, .2, .2, .2])

        self.elementary_transition_spec_ax = self.fig.add_subplot(self.grid_spec[0, 0])
        self.consolidated_transition_spec_ax = self.fig.add_subplot(self.grid_spec[1, 0], sharex=self.elementary_transition_spec_ax)
        self.waveform_ax = self.fig.add_subplot(self.grid_spec[2, 0], sharex=self.elementary_transition_spec_ax)
        self.snippets_ax = self.fig.add_subplot(self.grid_spec[3, 0], sharex=self.elementary_transition_spec_ax)
        
        self.elementary_transition_spec_ax.axis("on")
        self.consolidated_transition_spec_ax.axis("on")
        self.waveform_ax.axis("on")
        self.snippets_ax.axis("on")

        self.elementary_transition_spec_ax.grid(False)
        self.consolidated_transition_spec_ax.grid(False)
        self.waveform_ax.grid(False)
        self.snippets_ax.grid(False)

        self.consolidated_transition_spec_ax.set_ylim((-1, 1))
        
        self.color_by_genre = {
            None: "black",
            "high": "red",
            "low": "green",
            "tunnelEntrance": "blue",
            "tunnelExit": "orange",
            "highwayEntrance": "yellow",
            "highwayJunction": "magenta",
            "highwayExit": "red",
            "speedLimitRevocation": "purple",
            "trafficLight": "cyan"
        }

        self.splines = list()

        self.absolute_time_origin_in_ms = absolute_time_origin_in_ms
        self.absolute_time_horizon_in_ms = absolute_time_horizon_in_ms

        self.marker_elementary = None
        self.marker_consolidated = None

        self.marker_waveform = None
        self.time_offset_in_ms = waveform_time_offset_in_ms

        self.waveform_line = None

        self.snippet_lines = list()

        self.updating_strategy_text = None

    def draw_transition_spec(self, transition_spec: TransitionSpec):
        y = transition_spec.absolute_start_timestamp

        spline = list()

        for left_timestamp, genre, right_timestamp in transition_spec.iterate_parts(absolute=True):
            if right_timestamp:

                line = self.draw_line(
                    self.elementary_transition_spec_ax,
                    [left_timestamp, right_timestamp], [y, y], self.color_by_genre[genre], linewidth=2)
                
                # print((left_timestamp, y), (right_timestamp, y), self.color_by_genre[genre])

                spline.append(line)

                if right_timestamp > self.absolute_time_horizon_in_ms:
                    self.absolute_time_horizon_in_ms = right_timestamp

        self.splines.append(spline)

        self.elementary_transition_spec_ax.set_ylabel("Time of Estimation")
        self.elementary_transition_spec_ax.set_xlabel("t [ms]")
        self.elementary_transition_spec_ax.set_xlim(self.absolute_time_origin_in_ms, self.absolute_time_horizon_in_ms)
        self.elementary_transition_spec_ax.set_ylim(self.absolute_time_origin_in_ms - 1_000, self.absolute_time_horizon_in_ms)



    def draw_line(self, axes, x_data, y_data, color, linestyle="-", linewidth=3) -> mpl.lines.Line2D:
        line = mpl.lines.Line2D(
                x_data,
                y_data,
                linewidth=linewidth,
                color=color,
                linestyle=linestyle)

        axes.add_line(line)

        return line


    def set_consolidated_transition_spec(self, transition_spec: TransitionSpec, updating_strategy: UpdatingStrategy = None):
        # transition_spec

        # GRID LINES
        major_ticks = np.array(transition_spec.iterate_timestamps(absolute=True))
        self.consolidated_transition_spec_ax.set_xticks(major_ticks)
        # self.consolidated_transition_spec_ax.set_xticsk(major_ticks)
        # self.consolidated_transition_spec_ax.set_xticsk(major_ticks)

        self.elementary_transition_spec_ax.grid("on", which="major", axis="x", color="black", linewidth=2, linestyle="--")
        self.consolidated_transition_spec_ax.grid("on", which="major", axis="x", color="black", linewidth=2, linestyle="--")
        self.waveform_ax.grid("on", which="major", axis="x", color="black", linewidth=2, linestyle="--")

        # SPLINE
        for left_timestamp, genre, right_timestamp in transition_spec.iterate_parts(absolute=True):
            self.draw_line(self.consolidated_transition_spec_ax, 
                [left_timestamp, right_timestamp], 
                [0, 0], 
                self.color_by_genre[genre], 
                linewidth=2)

        # TEXT
        if updating_strategy:
            if self.updating_strategy_text in self.consolidated_transition_spec_ax.texts:
                self.consolidated_transition_spec_ax.texts.remove(self.updating_strategy_text)

            self.updating_strategy_text = self.consolidated_transition_spec_ax.text(
                0.5, 
                1, 
                f"{updating_strategy.name} (d_cp: {updating_strategy.diff_current_to_planned}, d_ca: {updating_strategy.diff_current_to_actual}, d_pa: {updating_strategy.diff_planned_to_actual})", 
                transform=self.consolidated_transition_spec_ax.transAxes,
                verticalalignment='bottom', 
                horizontalalignment='center',
                fontsize=25)


    def set_marker(self, marker_timestamp: int):
        if self.marker_elementary in self.elementary_transition_spec_ax.lines:
            self.elementary_transition_spec_ax.lines.remove(self.marker_elementary)
        
        if self.marker_consolidated in self.consolidated_transition_spec_ax.lines:
            self.consolidated_transition_spec_ax.lines.remove(self.marker_consolidated)

        self.marker_elementary = self.draw_line(
            self.elementary_transition_spec_ax, 
            [marker_timestamp, marker_timestamp], 
            self.elementary_transition_spec_ax.get_ylim(), 
            "red")

        self.marker_consolidated = self.draw_line(
            self.consolidated_transition_spec_ax, 
            [marker_timestamp, marker_timestamp], 
            self.consolidated_transition_spec_ax.get_ylim(), 
            "red")

    def set_waveform_marker(self, sample_marker: int):
        if self.marker_waveform:
            self.waveform_ax.lines.remove(self.marker_waveform)

        self.marker_waveform = self.draw_line(self.waveform_ax, [sample_marker, sample_marker], self.waveform_ax.get_ylim(), "red")


    def save(self, path: str):
        self.fig.savefig(path)


    def resample_waveform(self, waveform_np_int: np.ndarray) -> np.ndarray:
        waveform_np_f32 = (waveform_np_int / 255).astype(np.float32)
        waveform_tensor_f32 = torch.tensor(waveform_np_f32)          

        sample_rate_after_subsampling = 20.0
        sample_rate_original = 44100.0
        # must be float32 and mono in order to be fast (otherwise factor 20 slower!)
        resampled_tensor_f32 = torchaudio.transforms.Resample(sample_rate_original, sample_rate_after_subsampling, 'sinc_interpolation')(waveform_tensor_f32)
        resampled_np_int = (resampled_tensor_f32 * 255).type(torch.int16).numpy().flatten()

        idx = np.arange(len(resampled_np_int)) / sample_rate_after_subsampling * 1000

        return idx, resampled_np_int

    
    def draw_segment(self, segment: AudioSegment, sample_marker: int = None):
        if self.waveform_line:
            self.waveform_ax.lines.remove(self.waveform_line)

        segment = np.array(segment.get_array_of_samples())[::segment.channels]
        idx, resampled_np_int = self.resample_waveform(segment)

        x = idx
        y = resampled_np_int

        x = x + np.int32(self.time_offset_in_ms)        
        
        # We always plot x from 0 which is relevant if there is time offsite defined
        x_min, x_max, y_min, y_max = 0, np.max(x), np.min(y), np.max(y)
    
        self.waveform_ax.set_ylabel("Amplitude")
        self.waveform_ax.set_xlabel("t [ms]")
        self.waveform_ax.set_xlim(x_min, x_max)
        self.waveform_ax.set_ylim(y_min, y_max)

        self.waveform_line = self.draw_line(self.waveform_ax, x, y, "blue",linewidth=1)

        if sample_marker:
            self.set_waveform_marker(sample_marker)
    

    def draw_snippets(self, scheduled_snippets: List[ScheduledSnippet]):
        for snippet_line in self.snippet_lines:
            self.snippets_ax.lines.remove(snippet_line)
        
        self.snippet_lines = list()

        colors = {
            0: "red",
            1: "blue", 
            2: "yellow",
            3: "green",
            4: "cyan",
        }

        for i, scheduled_snippet in enumerate(scheduled_snippets): 
            segment = scheduled_snippet.get_audio_segment()
            segment = np.array(segment.get_array_of_samples())[::segment.channels]
            idx, resampled_np_int = self.resample_waveform(segment)

            x = idx
            y = resampled_np_int

            x = x + np.int32(scheduled_snippet.get_scheduled_start())        
            
            # We always plot x from 0 which is relevant if there is time offsite defined
            x_min, x_max, y_min, y_max = 0, np.max(x), np.min(y), np.max(y)
        
            self.snippets_ax.set_ylabel("Amplitude")
            self.snippets_ax.set_xlabel("t [ms]")
            self.snippets_ax.set_xlim(x_min, x_max)
            self.snippets_ax.set_ylim(y_min, y_max)

            self.snippet_lines.append(self.draw_line(self.snippets_ax, x, y, colors[i % len(colors)],linewidth=1))


if __name__ == "__main__":

    def test_transition_canvas(path_to_mp3: Path | str):
        path = Path(path_to_mp3)
        transition_canvas = TransitionCanvas()

        transition_canvas.draw_segment(pydub.AudioSegment.from_file(path), sample_marker = 60_122)

        transition_canvas.draw_transition_spec(
            TransitionSpec({
                15_000: "high",
                28_000: "low",
                66_000: "high",
            },
            absolute_start_timestamp=0)
        )
        transition_canvas.set_marker(0)
        
        transition_canvas.save("transitions_01.jpg")
        time.sleep(1)


        transition_canvas.draw_transition_spec(
            TransitionSpec({
                9_000: "high",
                22_000: "low",
                60_000: "high",
            },
            absolute_start_timestamp=6_000)
        )
        transition_canvas.set_marker(6_000)

        transition_canvas.save("transitions_02.jpg")
        time.sleep(1)


        transition_canvas.set_consolidated_transition_spec( TransitionSpec({
                15_000: "high",
                28_000: "low",
                66_000: "high",
            },
            absolute_start_timestamp=0))
        transition_canvas.set_marker(8_000)
        transition_canvas.save("transitions_03.jpg")


        transition_canvas.draw_transition_spec(
            TransitionSpec({
                2_000: "high",
                16_000: "low",
                54_000: "high",
            },
            absolute_start_timestamp=12_000)
        )
        transition_canvas.set_marker(12_000)
        transition_canvas.save("transitions_04.jpg")
        time.sleep(1)

        transition_canvas.draw_transition_spec(
            TransitionSpec({
                11_000: "low",
                46_000: "high",
            },
            absolute_start_timestamp=20_000)
        )
        transition_canvas.set_marker(20_000)
        transition_canvas.save("transitions_05.jpg")

    Fire(test_transition_canvas)