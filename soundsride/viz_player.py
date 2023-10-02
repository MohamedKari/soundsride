import time
from pydub import AudioSegment
import threading
from pathlib import Path

from .canvas.transition_spec_canvas import TransitionCanvas
from .player import Player
from fire import Fire

class VizPlayer:
    def __init__(self, write_canvas: bool = False):    
        self.canvas: TransitionCanvas = None
        self.playback_state = None
        self._player = None
        self._marker_y = None
        self.monitor_marker_thread = None
        self.write_canvas = write_canvas        
    
    def is_playing(self):
        return self.playback_state and self.playback_state.state == "running"

    def update_marker(self, x):
        self.canvas.set_waveform_marker(x)
        self.canvas.save("latest_audio.jpg")

    def _update_canvas(self, segment: AudioSegment):
        self.canvas = TransitionCanvas()
        self.canvas.draw_segment(segment)
        self.canvas.save("latest_audio.jpg")

    def play(self, segment: AudioSegment):
        self._player = Player(segment)
        self.playback_state = self._player.play_stream()
        
        if self.write_canvas:
            self._update_canvas(segment)
            self.monitor_marker_async(interval=.25)

    def swap_segment(self, segment: AudioSegment):
        # TODO: CANNOT SWAP BETWEEN SEGMENTS WITH DIFFERENT CHANNELS COUNTS
        if not self.is_playing():
            self.play(segment)
            return 

        self.playback_state.swap_segment = segment
        
        if self.write_canvas:
            self._update_canvas(segment)

    def stop(self):
        self.playback_state.request_stop = True

    def monitor_marker_async(self, interval: float = .1):
        def run():
            while True:
                if self.is_playing():
                    sample_position = self.playback_state.played_milliseconds
                    # print("UPDATING SAMPLE POSITION TO", sample_position)
                    self.update_marker(sample_position)
                
                time.sleep(interval)

        self.monitor_marker_thread = threading.Thread(target=run)
        self.monitor_marker_thread.start()
        

if __name__ == "__main__":
    import time

    def run_nonblocking(path_to_mp3: Path) -> None:
        viz_player = VizPlayer(write_canvas=True)
        print(f"Playing {path_to_mp3}...")
        viz_player.play(AudioSegment.from_file(path_to_mp3))
        viz_player.swap_segment(AudioSegment.from_file(path_to_mp3))
        
    Fire(run_nonblocking)
    print("running...", end="", flush=True)

    while True:
        time.sleep(1)
        print(".", end="", flush=True)
        
