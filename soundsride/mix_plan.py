from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple,  Optional
from dataclasses import dataclass
import time
import datetime
import json
import logging

from pydub import AudioSegment
import numpy as np
import scipy.signal as sps
from rich.console import Console
from rich.table import Table
import plotly.graph_objects as go

from .song import SongSnippet

from .service.soundsride_service_pb2 import UpdateTransitionSpecRequest

class InvalidFadingOperationException(Exception): pass
class TransitionTimeNegativeException(Exception): pass

class ScheduledSnippet:
    def __init__(self, song_snippet: SongSnippet, scheduled_transition_time: int, transition_mode: str):
        if scheduled_transition_time <= 0:
            raise TransitionTimeNegativeException()

        self.song_snippet = song_snippet
        self.scheduled_transition_time = scheduled_transition_time

        self.transition_mode = transition_mode
        
        self._fade_in_min = None
        self._fade_in_max = None
        self._fade_out_min = None
        self._fade_out_max = None

    def get_snippet_offset(self):
        return self.get_scheduled_transition() - self.song_snippet.get_pre_transition_duration()

    def mix_plan_time_to_snippet_time(self, mix_plan_time: int) -> int:
        return mix_plan_time - self.get_snippet_offset()
    
    def snippet_time_to_mix_plan_time(self, snippet_time: int) -> int:
        return snippet_time + self.get_snippet_offset()

    def get_scheduled_transition(self):
        return self.scheduled_transition_time

    def get_earliest_start(self):
        return max(0, self.scheduled_transition_time - self.song_snippet.get_pre_transition_duration())
    
    def get_latest_end(self):
        return self.scheduled_transition_time + self.song_snippet.get_post_transition_duration()

    def get_scheduled_start(self):
        if self._fade_in_min is None:
            return self.get_earliest_start()
        
        return self._fade_in_min

    def get_scheduled_end(self):
        if self._fade_out_max is None:
            return self.get_latest_end()

        return self._fade_out_max

    def get_audio_segment(self):
        base_snippet = self.song_snippet.get_audio_segment()
    
        snippet_relative_start = self.song_snippet.get_pre_transition_duration() - (
            self.get_scheduled_transition() - self.get_scheduled_start())

        snippet_relative_end = self.song_snippet.get_pre_transition_duration() + (
            self.get_scheduled_end() - self.get_scheduled_transition())

        segment = base_snippet[snippet_relative_start:snippet_relative_end] 

        assert (self._fade_in_min is None) == (self._fade_in_max is None)
        assert (self._fade_out_max is None) == (self._fade_out_min is None)

        if not self._fade_in_min is None:
            fade_in_duration = self._fade_in_max - self._fade_in_min
            if fade_in_duration:
                segment = segment.fade_in(fade_in_duration)
    
        if not self._fade_out_min is None:
            fade_out_duration = self._fade_out_max - self._fade_out_min
            if fade_out_duration:
                segment = segment.fade_out(fade_out_duration)

        return segment

    def set_fade_in(self, min_ts: int, max_ts: int):
        """
        Snippet will be 
        - set to volume 0% before min_ts
        - faded in linearly between min_ts and max_ts
        - set to volume 100% after max_ts

        Timestamps are relative to the schedule's origin.

        To have the snippet kick-in without a fade-in effect, set min_ts and max_ts to the same timestamp.
        """
        if min_ts is not None and min_ts < self.get_earliest_start():
            min_ts = self.get_earliest_start()
            # raise InvalidFadingOperationException(f"min_ts ({min_ts}) must be equal to or lie after earliest start ({self.get_earliest_start()}).")

        if max_ts is not None and max_ts > self.get_latest_end():
            max_ts = self.get_latest_end()
            # raise InvalidFadingOperationException("min_ts must be equal to or lie before latest end.")

        if min_ts and self._fade_out_min and self._fade_out_min < min_ts:
            raise InvalidFadingOperationException("min_ts must lie before fade_out_min")

        self._fade_in_min = min_ts
        self._fade_in_max = max_ts

    def set_fade_out(self, min_ts: int, max_ts: int):
        """
        Snippet will be 
        - set to volume 100% before min_ts
        - faded out linearly between min_ts and max_ts
        - set to volume 0% after max_ts

        Timestamps are relative to the schedule's origin.

        To have the snippet be muted without a fade-out effect, set min_ts and max_ts to the same timestamp.
        """


        if min_ts is not None and min_ts < self.get_earliest_start():
            raise InvalidFadingOperationException(f"min_ts  ({min_ts})  must be equal to or lie after earliest start ({self.get_earliest_start()}).")

        if max_ts is not None and max_ts > self.get_latest_end():
            raise InvalidFadingOperationException(f"max_ts ({max_ts}) must be equal to or lie before latest end ({self.get_latest_end()}).")

        if min_ts and self._fade_in_max and self._fade_in_max > min_ts:
            raise InvalidFadingOperationException(f"min_ts must ({min_ts}) lie after fade_in_max ({self._fade_in_max})")

        self._fade_out_min = min_ts
        self._fade_out_max = max_ts

    def extend(self, required_post_transition_length: int, extension_strategy: str = "auto"):
        raise NotImplementedError
    
        if extension_strategy == "auto":
            pass
        if extension_strategy == "repeat_beat":
            pass
        elif extension_strategy == "repeat_bar":
            pass
        elif extension_strategy == "repeat_phase":
            pass
        elif extension_strategy == "include_next_phase":
            pass
        elif extension_strategy == "strech_bpm":
            pass
        elif extension_strategy == "traktor_freeze_effect":
            pass
        else: 
            raise ValueError("extension_strategy unkown")
            
        

@dataclass()
class GenreTransition:
    genre_transition_timestamp: int
    pre_transition_genre: str
    post_transition_genre: str

class SnippetTransition:
    pass

class GenreTransitionAtZeroException(Exception):
    pass

class TransitionSpec:

    def __init__(self, 
            genre_transitions: Dict[int, str], 
            transition_ids: List[int] = None,
            absolute_start_timestamp: int = None) -> None:

        assert isinstance(genre_transitions, dict)

        self.genre_transitions = genre_transitions
        self.transition_ids = transition_ids
        self.absolute_start_timestamp = absolute_start_timestamp

        # if 0 in self.genre_transitions:
        #     raise GenreTransitionAtZeroException()

    @staticmethod
    def from_spec_file(spec_file: Path) -> "TransitionSpec":
        genre_transition_specs = spec_file.read_text().splitlines(keepends=False)

        genre_transitions = dict()

        for genre_transition_spec in genre_transition_specs[:]:
            genre_transition_timestamp, post_transition_genre = genre_transition_spec.split(" ")
            genre_transitions[int(genre_transition_timestamp)] = post_transition_genre

        return TransitionSpec(genre_transitions)
    
    @staticmethod
    def from_spec_protobuf(spec_protobuf: UpdateTransitionSpecRequest, absolute_start_timestamp: int = None, negative_ett_handling: str = "raise"):
        """
        spec_dict should like this: 
        ```py
        {
            'transitions': 
                [
                    {
                        'transitionId': '41', 
                        'transitionToGenre': 'low', 
                        'estimatedTimeToTransition': -1.0, 
                        'estimatedGeoDistanceToTransition': -1.0
                    },
                    {
                        'transitionId': '115', 
                        'transitionToGenre': 'high', 
                        'estimatedTimeToTransition': 51.0, 
                        'estimatedGeoDistanceToTransition': 510.96432
                    },
                    {
                        'transitionId': '205', 
                        'transitionToGenre': 'low', 
                        'estimatedTimeToTransition': 141.0, 
                        'estimatedGeoDistanceToTransition': 1242.3219
                    }
                ], 
            'sessionId': 0, 
            'initialGenre': ''
        }
        ```
        """

        if len(spec_protobuf.transitions) == 0:
            TransitionSpec(dict(), absolute_start_timestamp=absolute_start_timestamp)

        transition_ids = list()
        genre_transitions = dict()
        for next_transition in spec_protobuf.transitions[0:]:
            if next_transition.estimated_time_to_transition < 0:
                if negative_ett_handling == "skip":
                    continue
                if negative_ett_handling == "raise":
                    raise ValueError("ETT negative")
                
                if next_transition.estimated_time_to_transition in genre_transitions:
                    raise ValueError("ETTs must be unique")

            transition_ids.append(next_transition.transitionId)
            genre_transitions[int(next_transition.estimated_time_to_transition) * 1000] = next_transition.transition_to_genre 


        return TransitionSpec(genre_transitions, transition_ids=transition_ids, absolute_start_timestamp=absolute_start_timestamp)

    def iterate_parts(self, absolute=False) -> Iterable[Tuple[int, str, int]]:
        left_timestamp = 0
        genre = None
        
        parts = list()
        
        if absolute:
            offset = self.absolute_start_timestamp
        else:
            offset = 0

        for next_timestamp, next_genre in self.genre_transitions.items():            
            
            parts.append((left_timestamp + offset, genre, next_timestamp + offset))

            left_timestamp = next_timestamp
            genre = next_genre

        parts.append((left_timestamp + offset, genre, None))

        return parts

    def iterate_transitions(self, absolute=False) -> Iterable[Tuple[str, int, str]]:
        left_genre = None
        
        transitions = list()
        
        if absolute:
            offset = self.absolute_start_timestamp
        else:
            offset = 0

        for timestamp, right_genre in self.genre_transitions.items():            
            
            transitions.append((left_genre, timestamp + offset, right_genre))

            left_genre = right_genre

        return transitions


    def iterate_timestamps(self, absolute=False):
        if absolute:
            offset = self.absolute_start_timestamp
            return [timestamp + offset for timestamp in self.genre_transitions.keys()]
        else:
            return list(self.genre_transitions.keys())

        
    def get_timestamp_and_genre_by_id(self, transition_id: int, absolute=False) -> Optional[Tuple[int, str]]:
        if transition_id not in self.transition_ids:
            return None

        idx = self.transition_ids.index(transition_id)
        timestamp, right_genre = list(self.genre_transitions.items())[idx]
        
        if absolute:
            timestamp += self.absolute_start_timestamp

        return timestamp, right_genre 

    def get_first_transition_timestamp_after_timestamp(self, timestamp: int) -> int:

        for next_timestamp in self.iterate_timestamps():
            if next_timestamp > timestamp:
                return timestamp
        
    def absolute_genre_transitions(self) -> Dict[int, str]:
        return dict([(timestamp + self.absolute_start_timestamp, genre) for timestamp, genre in self.genre_transitions.items()])

    def __repr__(self, with_absolute=False) -> str:
        if self.genre_transitions:
            _repr = f"{self.absolute_start_timestamp} - "
            genre_transition_by_id = list(zip(self.transition_ids, self.genre_transitions.items()))
            if with_absolute:
                _repr += ", ".join([
                    f"{transition_id}: {transition_timestamp} ({transition_timestamp + (self.absolute_start_timestamp or 0)})) -> {to_genre}"
                    for transition_id, (transition_timestamp, to_genre) 
                    in genre_transition_by_id
                ])
            else:
                _repr += ", ".join([
                    f"{transition_id}: {transition_timestamp} -> {to_genre}"
                    for transition_id, (transition_timestamp, to_genre) 
                    in genre_transition_by_id
                ])

            return _repr
        
        return ""
 

class MixPlanPrintable():
    pass

class SnippetStartEvent(MixPlanPrintable):
    def __init__(self, timestamp: int, snippet_id: int, song_start_timestamp: int):
        self.timestamp = timestamp
        self.snippet_id = snippet_id
        self.song_start_timestamp = song_start_timestamp

    def __str__(self):
        return f"S{self.snippet_id} starts with song second {self.song_start_timestamp}"
    
    def __repr__(self) -> str:
        return f"SnippetStartEvent({self.timestamp}, {self.snippet_id}, {self.song_start_timestamp})"

    def __eq__(self, other: "SnippetStartEvent"):
        if isinstance(other, SnippetStartEvent):
            return self.timestamp == other.timestamp \
                and self.snippet_id == other.snippet_id \
                and self.song_start_timestamp == other.song_start_timestamp
        return False

class SnippetEndEvent(MixPlanPrintable):
    def __init__(self, timestamp: int, snippet_id: int, song_end_timestamp: int):
        self.timestamp = timestamp
        self.snippet_id = snippet_id
        self.song_end_timestamp = song_end_timestamp

    def __str__(self):
        return f"S{self.snippet_id} ends with song second {self.song_end_timestamp}"
    
    def __repr__(self) -> str:
        return f"SnippetEndEvent({self.timestamp}, {self.snippet_id}, {self.song_end_timestamp})"

    def __eq__(self, other: "SnippetEndEvent"):
        if isinstance(other, SnippetEndEvent):
            return self.timestamp == other.timestamp \
                and self.snippet_id == other.snippet_id \
                and self.song_end_timestamp == other.song_end_timestamp
        return False

class GenreTransitionEvent(MixPlanPrintable):
    def __init__(self, timestamp: int, snippet_id: int, song_transition_ts: int, pre_transition_genre: str, post_transition_genre: str):
        self.timestamp = timestamp
        self.snippet_id = snippet_id
        self.song_transition_ts = song_transition_ts
        self.pre_transition_genre = pre_transition_genre
        self.post_transition_genre = post_transition_genre

    def __str__(self):
        return (
            f"S{self.snippet_id} transitions from {self.pre_transition_genre} "
            f"to {self.post_transition_genre} with song second {self.song_transition_ts}"
        )

    def __repr__(self) -> str:
        return (
            f"GenreTransitionEvent({self.timestamp}, {self.snippet_id}, {self.song_transition_ts}, "
            f"{self.pre_transition_genre}, {self.post_transition_genre})"
        )

    def __eq__(self, other: "GenreTransitionEvent"):
        if isinstance(other, GenreTransitionEvent):
            return self.timestamp == other.timestamp \
                and self.snippet_id == other.snippet_id \
                and self.song_transition_ts == other.song_transition_ts \
                and self.pre_transition_genre == other.pre_transition_genre \
                and self.post_transition_genre == other.post_transition_genre
        return False

class GenrePhase(MixPlanPrintable):
    def __init__(self, genre: str, start_ts: int, end_ts: int):
        self.genre = genre
        self.start_ts = start_ts
        self.end_ts = end_ts

    def __str__(self):
        return f"{self.genre} from {self.start_ts} to {self.end_ts}"

    def __repr__(self) -> str:
        return f"GenrePhase({self.genre}, {self.start_ts}, {self.end_ts})"
    
    def __eq__(self, other: "GenrePhase"):
        if isinstance(other, GenrePhase):
            return self.genre == other.genre \
                and self.start_ts == other.start_ts \
                and self.end_ts == other.end_ts

        return False

class MixPlan:
    def __init__(self) -> None:
        self._scheduled_snippets: List[ScheduledSnippet] = list()
        # self.genre_transitions: List[SpecifiedGenreTransition] = list()
        self.transition_safe_zone_length = 5_000
        self.cross_fade_duration = 3_000
        self.long_cross_fade_duration = 25_000

    @property
    def scheduled_snippets(self) -> List[ScheduledSnippet]:
        return sorted(
            self._scheduled_snippets, 
            key=lambda scheduled_snippet: scheduled_snippet.get_scheduled_transition())

    # def _validate(self):
        # pass

    def add_snippet_transition(self,
                               snippet: SongSnippet,
                               planned_genre_transition_time: int,
                               snippet_transition_mode: str):
        """
        Args:
        - snippet
        - planned_genre_transition_time: 
            planned_genre_transition_time relative to the MixPlan's origin.
            snippet's planned_genre_transition_time will be aligned with this planned_genre_transition_time
        - snippet_transition_time (int): Automatically determined if none is passed.
        - snippet_transition_mode (str): One of the following: CROSS_FADE | HARD_CUT | OVERLAY
        """

        scheduled_snippet = ScheduledSnippet(
            snippet,
            planned_genre_transition_time, 
            snippet_transition_mode
        )

        self._scheduled_snippets.append(
            scheduled_snippet
        )

    def to_list(self) -> List[MixPlanPrintable]:
        l = list()
        for scheduled_snippet in self.scheduled_snippets:
            start_ts, transition_ts, end_ts = (
                scheduled_snippet.get_scheduled_start(),
                scheduled_snippet.get_scheduled_transition(),
                scheduled_snippet.get_scheduled_end()
            )

            l.append(SnippetStartEvent(
                start_ts,
                scheduled_snippet.song_snippet.snippet_id,
                scheduled_snippet.song_snippet.snippet_start_timestamp))

            l.append(GenrePhase(
                scheduled_snippet.song_snippet.pre_transition_genre,
                start_ts,
                transition_ts))

            l.append(GenreTransitionEvent(
                transition_ts,
                scheduled_snippet.song_snippet.snippet_id,
                scheduled_snippet.song_snippet.genre_transition_timestamp,
                scheduled_snippet.song_snippet.pre_transition_genre,
                scheduled_snippet.song_snippet.post_transition_genre))

            l.append(GenrePhase(
                scheduled_snippet.song_snippet.post_transition_genre,
                transition_ts,
                end_ts))

            l.append(SnippetEndEvent(
                end_ts,
                scheduled_snippet.song_snippet.snippet_id,
                scheduled_snippet.song_snippet.snippet_end_timestamp))

        return l

    def __str__(self):
        return "\n".join([str(i) for i in self.to_list()])

    def print_to_console(self):
        console = Console()
        table = Table(show_header=True)
        table.add_column("Snippet Events", justify="right", header_style="bold blue")
        table.add_column("Global Time", justify="center", header_style="bold")
        table.add_column("Genre Events", justify="left", header_style="bold magenta")

        for mix_plan_printable in self.to_list():
            row = None
            if isinstance(mix_plan_printable, SnippetStartEvent):
                row = (
                    f"[dodger_blue1]{str(mix_plan_printable)}[/dodger_blue1]", 
                    f"[dodger_blue1]{mix_plan_printable.timestamp}[/dodger_blue1]", 
                    ""
                )
            elif isinstance(mix_plan_printable, GenrePhase):
                row = (
                    "", 
                    f"[magenta]{mix_plan_printable.start_ts} to {mix_plan_printable.end_ts}[/magenta]", 
                    f"[magenta]{mix_plan_printable.genre}[/magenta]"
                )
            elif isinstance(mix_plan_printable, GenreTransitionEvent):
                row = (
                    f"[blue]{str(mix_plan_printable)}[/blue]",
                    f"[magenta]{mix_plan_printable.timestamp}[/magenta]",
                    f"[magenta]Genre transitions from {mix_plan_printable.pre_transition_genre} "
                    f"to {mix_plan_printable.post_transition_genre}[/magenta]"
                )
            elif isinstance(mix_plan_printable, SnippetEndEvent):
                row = (
                    f"[blue_violet]{str(mix_plan_printable)}[/blue_violet]", 
                    f"[blue_violet]{mix_plan_printable.timestamp}[/blue_violet]", 
                    ""
                )
            else:
                raise TypeError("Unkown type")

            table.add_row(*row)

        console.print(table)      

    def get_length(self):
        """
        Returns the end_timestamp of the last snippet
        """
        last_scheduled_snippet = self.scheduled_snippets[-1]
        return last_scheduled_snippet.get_scheduled_end()


    def to_audio_segment(self):
        segment = AudioSegment.silent(self.get_length())
        # print("Silent segment has ", len(segment), " ms")
        
        for scheduled_snippet in self.scheduled_snippets:
            segment = segment.overlay(scheduled_snippet.get_audio_segment(), position=scheduled_snippet.get_scheduled_start())

        # segment.export(datetime.datetime.fromtimestamp(time.time()).isoformat().replace(":", "-") + ".mp3")
        
        return segment

    # Transitioning
    def _get_overlap_zones(self) -> List[Optional[Tuple[int, int]]]: # pylint: disable=unsubscriptable-object
        overlap_zones = list()

        scheduled_snippets = self.scheduled_snippets
        prev_scheduled_snippet = scheduled_snippets[0]

        for scheduled_snippet in scheduled_snippets[1:]:
            
            # print(
            #    "Prev snippet starts at ", prev_scheduled_snippet.get_scheduled_start(), 
            #    ", transitions at ", prev_scheduled_snippet.get_scheduled_transition(), 
            #    ", and ends ", prev_scheduled_snippet.get_scheduled_end(), ".")


            # print(
            #     "Current snippet starts at ", scheduled_snippet.get_scheduled_start(), 
            #     ", transitions at ", scheduled_snippet.get_scheduled_transition(), 
            #     ", and ends ", scheduled_snippet.get_scheduled_end(), ".")
            
            overlaps = prev_scheduled_snippet.get_latest_end() > scheduled_snippet.get_earliest_start()
            
            if overlaps:
                transitioning_zone_start = max(prev_scheduled_snippet.get_scheduled_transition(), scheduled_snippet.get_earliest_start())
                transitioning_zone_end = min(prev_scheduled_snippet.get_latest_end(), scheduled_snippet.get_scheduled_transition())
                overlap_zones.append((transitioning_zone_start, transitioning_zone_end))
            else:
                overlap_zones.append(None)

            prev_scheduled_snippet = scheduled_snippet

        return overlap_zones

    def _get_best_cut_candidate(self, ending_snippet, starting_snippet, overlap_zone_start, overlap_zone_end) -> int:
        cut_candidates = [int((overlap_zone_start + overlap_zone_end) / 2)]
        return cut_candidates[0]

    def _get_cross_fade_zone_candidate(self, 
            first_snippet: ScheduledSnippet, 
            second_snippet: ScheduledSnippet, 
            overlap_zone_start: int, 
            overlap_zone_end: int
            ) -> Tuple[int, int]:

        # Transition spec
        # |--------------------|--------------------|--------------------|--------------------|
        #            ^                                                   ^         
        #       first trigger 1                                    second trigger
        #
        #
        # Snippets
        # 1: --------++++++++++++++++++++++++++++++++++++++++++
        # 2:                                   --------------------------++++++++++++++++ 
        #
        #
        # 1: --------++++++++++++++++++++++++++++
        # 2:                                   --------------------------++++++++++++++++ 
        #
        #
        # Zone Computations
        #            <-----------------trigger-distance----------------->
        #  
        # 
        #                                      <-overlap-zone->      
        #            <--safe-zone--|-----working-zone-----|--safe-zone-->
        #                                      <transition>
        #                                            <fade>
        #
        # The transition zone is constrained
        # - by the working zone and
        # - by the overlap zone,
        # 
        # The extension step is responsible for ensuring that the length of transition zone is equal to 
        # or longer than the cross-fade duration.

       

        first_trigger = first_snippet.get_scheduled_transition()
        second_trigger = second_snippet.get_scheduled_transition()

        logging.getLogger(__name__).debug("Left snippet's transition scheduled for %s", first_trigger)
        logging.getLogger(__name__).debug("Right snippet's transition scheduled for %s", second_trigger)

        working_zone_start = first_trigger + self.transition_safe_zone_length
        working_zone_end = second_trigger - self.transition_safe_zone_length
        working_zone_duration = working_zone_end - working_zone_start

        logging.getLogger(__name__).debug("Working zones starts at %s and ends at %s with a length of %s", working_zone_start, working_zone_end, working_zone_duration)

        if working_zone_duration < self.cross_fade_duration:
            logging.getLogger(__name__).debug("Working zone shorter than cross_fade_duration!")
            return None

        transition_zone_start =  max(overlap_zone_start, working_zone_start) # pylint: disable=unused-variable
        transition_zone_end = min(overlap_zone_end, working_zone_end)
        transition_zone_length = transition_zone_end - transition_zone_start

        logging.getLogger(__name__).debug("Overlap zone starts at %s and ends at %s", overlap_zone_start, overlap_zone_end)

        logging.getLogger(__name__).debug("Transition zone starts at %s and ends at %s", transition_zone_start, transition_zone_end)

        cross_fade_duration = min(self.cross_fade_duration, transition_zone_length)

        if second_snippet.transition_mode == "LATE":
            fade_zone_end = transition_zone_end
            fade_zone_start = fade_zone_end - cross_fade_duration

        elif second_snippet.transition_mode == "MEDIUM":
            fade_zone_start = int(transition_zone_start + (transition_zone_end - transition_zone_start) / 2 - cross_fade_duration / 2)
            fade_zone_end = int(transition_zone_start + (transition_zone_end - transition_zone_start) / 2 + cross_fade_duration / 2)

        elif second_snippet.transition_mode == "SLOW":
            fade_zone_end = transition_zone_end
            fade_zone_start = fade_zone_end - self.long_cross_fade_duration
        
        elif second_snippet.transition_mode == "EARLY":
            fade_zone_start = transition_zone_start
            fade_zone_end = fade_zone_start + self.cross_fade_duration

        logging.getLogger(__name__).debug("Fade zone starts at %s and ends at %s", fade_zone_start, fade_zone_end)            

        return fade_zone_start, fade_zone_end
    
    def set_snippet_transitions(self, transition_type="cut"):
        if not self.scheduled_snippets:
            return

        # For Snippet Overlaps
        overlap_zones = self._get_overlap_zones()

        for snippet_id, overlap_zone in enumerate(overlap_zones):
            if not overlap_zone:
                continue
            
            overlap_zone_start, overlap_zone_end = overlap_zone

            ending_snippet, starting_snippet = \
                self.scheduled_snippets[snippet_id], self.scheduled_snippets[snippet_id + 1]

            if transition_type == "cut":
                best_cut_candidate = self._get_best_cut_candidate(
                    ending_snippet, 
                    starting_snippet,
                    overlap_zone_start, 
                    overlap_zone_end)

                fade_out_start, fade_in_start = best_cut_candidate, best_cut_candidate
                fade_out_end, fade_in_end = best_cut_candidate, best_cut_candidate

            elif transition_type == "crossfade":
                # TODO: These must not leave the safe overlap zone
                fade_zone = self._get_cross_fade_zone_candidate(
                    self.scheduled_snippets[snippet_id],
                    self.scheduled_snippets[snippet_id + 1],
                    overlap_zone_start,
                    overlap_zone_end)

                if fade_zone:
                    fade_zone_start, fade_zone_end = fade_zone

                    fade_out_start, fade_in_start = fade_zone_start, fade_zone_start
                    fade_out_end, fade_in_end = fade_zone_end, fade_zone_end
                else:
                    print("Cannot cross-fade because working zone is too short or doesn't exist. Cutting hard.")
                    best_cut_candidate = self._get_best_cut_candidate(
                        ending_snippet, 
                        starting_snippet,
                        overlap_zone_start, 
                        overlap_zone_end)

                    fade_out_start, fade_in_start = best_cut_candidate, best_cut_candidate
                    fade_out_end, fade_in_end = best_cut_candidate, best_cut_candidate

            else:
                raise ValueError("transition_type invalid")
                
            ending_snippet.set_fade_out(fade_out_start, fade_out_end)
            starting_snippet.set_fade_in(fade_in_start, fade_in_end)

    # For Snippet Starts and Ends


    def get_last_scheduled_snippet_before_timestamp(self, timestamp: int):
        last_scheduled_snippet = None

        for scheduled_snippet in self.scheduled_snippets:
            scheduled_transition = scheduled_snippet.get_scheduled_transition()
            
            if scheduled_transition > timestamp:
                return last_scheduled_snippet

            last_scheduled_snippet = scheduled_snippet
        
        return last_scheduled_snippet

class OnTheFlyIDs():
    def __init__(self):
        self._l = list()

    def __getitem__(self, name):
        if name not in self._l:
            self._l.append(name)        
        
        return self._l.index(name)


class MixPlanViz:
    def __init__(self):
        # self.canvas = np.full((1080, 1920, 3), 255, np.uint8)
         
        # self.timeline_offset_x_px = 50
        # self.timeline_offset_y_px = 50
        # self.timeline_length_px = 1500
        self.fig = go.Figure()
        self.annotations: List[dict] = list()
        self.visualized_sample_rate = 100
        self.track_counter = 0
        self.genre_phase_counter = 0
        self.colors = [
            "green", 
            "blue", 
            "yellow", 
            "magenta", 
            "cyan", 
            "brown",
            "purple"
        ]
        self.genre_color_ids = OnTheFlyIDs()
    
    def viz_mix_plan(self, mix_plan: MixPlan):
        for scheduled_snippet in mix_plan.scheduled_snippets:
            self.add_scheduled_snippet(scheduled_snippet)

    def viz_transition_spec(self, transition_spec: TransitionSpec):
        genre_transitions = list(transition_spec.genre_transitions.items())
        prev_genre_transition_timestamp, prev_post_transition_genre = genre_transitions[0]
        last_phase_dummy_extension = 20_000

        for genre_transition_timestamp, post_transition_genre in genre_transitions[1:]:
            self.add_genre_phase(prev_post_transition_genre, prev_genre_transition_timestamp, genre_transition_timestamp)
            prev_genre_transition_timestamp = genre_transition_timestamp
            prev_post_transition_genre = post_transition_genre

        self.add_genre_phase(prev_post_transition_genre, prev_genre_transition_timestamp, prev_genre_transition_timestamp + last_phase_dummy_extension)

    def viz_segment(self, segment: AudioSegment):
        samples = segment.get_array_of_samples()
        samples = np.array(samples)
        samples = samples.reshape(segment.channels, -1, order='F') # pylint: disable=redundant-keyword-arg
        samples = samples[0]
        number_of_samples = round(len(samples) * float(self.visualized_sample_rate) / segment.frame_rate)
        samples = sps.resample(samples, number_of_samples)
        samples = samples / np.max(samples)

        self.fig.add_trace(go.Scatter(
            x=np.linspace(0, len(segment), num=len(samples)),
            y=samples - 2,
            line={
                "color": "black"
            }
        ))

    def add_scheduled_snippet(self, scheduled_snippet: ScheduledSnippet) -> None:
        start_ts                            = scheduled_snippet.get_scheduled_start()
        transition_ts                       = scheduled_snippet.get_scheduled_transition()
        end_ts                              = scheduled_snippet.get_scheduled_end()
        pre_transition_genre                = scheduled_snippet.song_snippet.pre_transition_genre
        post_transition_genre               = scheduled_snippet.song_snippet.post_transition_genre
        snippet_start_timestamp             = scheduled_snippet.song_snippet.snippet_start_timestamp 
        snippet_genre_transition_timestamp  = scheduled_snippet.song_snippet.genre_transition_timestamp
        snippet_end_timestamp               = scheduled_snippet.song_snippet.snippet_end_timestamp 
        segment                             = scheduled_snippet.get_audio_segment()

        # print("start_ts", start_ts)
        # print("transition_ts", transition_ts)
        # print("end_ts", end_ts)

        # print("snippet_start_timestamp", snippet_start_timestamp)
        # print("snippet_genre_transition_timestamp", snippet_genre_transition_timestamp)
        # print("snippet_end_timestamp", snippet_end_timestamp)        

        samples = segment.get_array_of_samples()
        samples = np.array(samples)
        samples = samples.reshape(segment.channels, -1, order='F') # pylint: disable=redundant-keyword-arg
        samples = samples[0]

        # print("original len(samples)", len(samples))
        # print("original frame_rate", scheduled_snippet.song_snippet.base_audio_segment.frame_rate)
        
        number_of_samples = round(len(samples) * float(self.visualized_sample_rate) / scheduled_snippet.song_snippet.base_audio_segment.frame_rate)
        samples = sps.resample(samples, number_of_samples)

        samples = samples / np.max(samples)

        # print("new len(samples)", len(samples))
        # print("self.visualized_sample_rate", self.visualized_sample_rate)

        n_pre_transition_samples = int(self.visualized_sample_rate * (transition_ts - start_ts) / 1000)
        n_post_transition_samples = len(samples) - n_pre_transition_samples

        # print("n_pre_transition_samples", n_pre_transition_samples)
        # print("n_post_transition_samples", n_post_transition_samples)

        vertical_snippet_offset = self.track_counter * 2 + 2

        # Pre-Transition Genre
        self.fig.add_trace(go.Scatter(
            x=np.linspace(start_ts, transition_ts, num=n_pre_transition_samples+1),
            y=samples[:n_pre_transition_samples+1] + vertical_snippet_offset,
            line={
                # TODO: round-robin to avoid color supply exhaustion
                "color": self.colors[self.genre_color_ids[pre_transition_genre]]
            }
        ))

        self.annotations.append({
            "x": start_ts,
            "y": vertical_snippet_offset,
            "xanchor": "right",
            "yanchor": "bottom",
            "text": pre_transition_genre,
            "showarrow": True
        })

        # Post-Transition Genre
        self.fig.add_trace(go.Scatter(
            x=np.linspace(transition_ts, end_ts, num=n_post_transition_samples),
            y=samples[n_pre_transition_samples+1:] + vertical_snippet_offset,
            line={
                "color": self.colors[self.genre_color_ids[post_transition_genre]]
            }
        ))

        self.annotations.append({
            "x": end_ts,
            "y": vertical_snippet_offset,
            "xanchor": "left",
            "yanchor": "top",
            "text": post_transition_genre,
            "showarrow": True
        })

        self.track_counter += 1

    def add_genre_phase(self, genre: str, start_ts: int, end_ts: int):
        self.fig.add_trace(go.Scatter(
            x=[start_ts, end_ts],
            y=[0, 0],
            line=dict(color=self.colors[self.genre_color_ids[genre]])))

        self.annotations.append({
            "x": (start_ts + end_ts) / 2,
            "y": 0,
            "xanchor": "center",
            "yanchor": ["bottom", "top"][self.genre_phase_counter % 2],
            "text": genre,
            "showarrow": True
        })

        self.genre_phase_counter += 1


    def show(self):
        # self.fig.update_yaxes(type='category')
        self.fig.update_layout(annotations=self.annotations)
        self.fig.update_layout({
           "xaxis.rangemode": "tozero"
        })

        self.fig.show()

    def get_fig(self):
        self.fig.update_layout(annotations=self.annotations)
        self.fig.update_layout({
           "xaxis.rangemode": "tozero", 
           "showlegend": False
        })
    
        return self.fig