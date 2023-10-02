from os import stat
import time
from typing import Literal, Union

from pydub import AudioSegment
from pyaudio import PyAudio, Stream
from concurrent.futures import ThreadPoolExecutor, Future
import fire

class PlaybackState():
    def __init__(self, sample_rate: int):
        self.played_milliseconds = 0
        self.sample_rate: int = sample_rate
        self.playback_future: Future = None
        self.request_stop: bool = False
        self.state: Union[Literal["idle"], Literal["running"], Literal["finished"]] = \
            "idle" # pylint: disable=unsubscriptable-object
        self.swap_segment: AudioSegment = None

    def get_sample_position(self):
        return int(self.played_milliseconds / 1000 * self.sample_rate)


class Player():
    
    def __init__(self, segment: AudioSegment):
        self._segment = segment
    
    def play_stream(self) -> PlaybackState:
        p = PyAudio()
        
        def playback_stream(segment: AudioSegment, playback_state: PlaybackState):
            sample_format = p.get_format_from_width(segment.sample_width)
            channels = segment.channels
            rate = segment.frame_rate

            stream = p.open(format=sample_format, channels=channels, rate=rate, output=True)

            chunk_length = 250 # ms
            playback_state.state = "running"

            i = 0
            left = right = 0
            while right < len(segment): 
                if playback_state.request_stop:
                    break

                if playback_state.swap_segment: 
                    segment = playback_state.swap_segment
                    playback_state.swap_segment = None
                    
                    # Safe-guard against swapping in a shorter segment that the original segment
                    if len(segment) < left:
                        break

                left = i * chunk_length
                right = (i + 1) * chunk_length
                right = min(right, len(segment))
                
                if left == right:
                    break

                stream.write(segment[left:right].raw_data)
                
                playback_state.played_milliseconds += chunk_length

                i += 1
            
            playback_state.state = "finished"

        playback_state = PlaybackState(self._segment.frame_rate)

        executor = ThreadPoolExecutor(1)
        playback_future = executor.submit(playback_stream, self._segment, playback_state)

        playback_state.playback_future = playback_future

        return playback_state


class CLI():
    
    @staticmethod
    def play(path_to_mp3: str):
            
        player = Player(AudioSegment.from_mp3(path_to_mp3))
        _playback_state = player.play_stream()

        while not _playback_state.playback_future.done():
            print(_playback_state.played_milliseconds / 1000, _playback_state.get_sample_position())
            time.sleep(0.1)

if __name__ == "__main__":
    # python -m soundsride.player play $PATH_TO_MP3
    fire.Fire(CLI.play)
