import logging
from os import isatty
from pathlib import Path
from typing import List, Dict

from pydub import AudioSegment

class SongSnippet:
    def __init__(self,
                 base_audio_segment: AudioSegment,
                 snippet_id: int,
                 pre_transition_genre: str,
                 post_transition_genre: str,
                 snippet_start_timestamp: int,
                 genre_transition_timestamp: int,
                 snippet_end_timestamp: int) -> None:

        self.base_audio_segment = base_audio_segment
        self.snippet_id = snippet_id
        self.pre_transition_genre = pre_transition_genre
        self.post_transition_genre = post_transition_genre
        
        self.snippet_start_timestamp = snippet_start_timestamp 
        # set to 0 to avoid silences

        self.genre_transition_timestamp = genre_transition_timestamp
        
        self.snippet_end_timestamp = snippet_end_timestamp
        # set to len(base_audio_segment) to avoid silences

    def get_length(self) -> int:
        return self.snippet_end_timestamp - self.snippet_start_timestamp

    def get_pre_transition_duration(self):
        return self.genre_transition_timestamp - self.snippet_start_timestamp

    def get_post_transition_duration(self):
        return self.snippet_end_timestamp - self.genre_transition_timestamp

    def get_audio_segment(self) -> AudioSegment:
        return self.base_audio_segment[self.snippet_start_timestamp:self.snippet_end_timestamp]

class Song:
    @staticmethod
    def _parse_metadata_file(metadata_file: Path):
        print(metadata_file)
        metadata_text = metadata_file.read_text()
        phases = metadata_text.splitlines(keepends=False)

        metadata_dict: Dict[int, str] = dict()

        for phase in phases:
            phase_start_timestamp, phase_mood = phase.split(" ")
            phase_start_timestamp = int(phase_start_timestamp)

            metadata_dict[phase_start_timestamp] = phase_mood

        transition_table: Dict[str, Dict[str, List[int]]] = dict()

        metadata_list = list(metadata_dict.items())

        for i in range(0, len(metadata_list) - 1):
            _, pre_transition_genre = metadata_list[i]
            transition_timestamp, post_transition_genre = metadata_list[i + 1]

            post_transitions = transition_table.get(
                pre_transition_genre, dict())
            transition_table[pre_transition_genre] = post_transitions

            timestamps = post_transitions.get(post_transition_genre, list())
            post_transitions[post_transition_genre] = timestamps

            timestamps.append(transition_timestamp)

        return metadata_dict, transition_table

    def __init__(self, audio_file: Path, metadata_file: Path):
        self.audio_segment = AudioSegment.from_mp3(str(audio_file))
        self.metadata_dict, self.transition_table = Song._parse_metadata_file(
            metadata_file)

    def get_number_of_phases(self):
        return len(self.metadata_dict)
    
    def get_number_of_snippets(self):
        return self.get_number_of_phases() - 1
    
    def get_number_of_genre_transitions(self):
        return self.get_number_of_snippets()

    def get_full_snippets_by_genres(self, pre_transition_genre: str, post_transition_genre: str) -> SongSnippet:
        transition_timestamps = self.transition_table[pre_transition_genre][post_transition_genre]       

        snippets = list()
        for transition_timestamp in transition_timestamps:
            snippet_id = transition_in_song_id = sorted(
                self.metadata_dict.keys()).index(transition_timestamp)

            snippet_start_timestamp = list(self.metadata_dict.keys())[
                transition_in_song_id - 1]

            if transition_in_song_id == self.get_number_of_genre_transitions():
                snippet_end_timestamp = len(self.audio_segment)
            else: 
                snippet_end_timestamp = list(self.metadata_dict.keys())[
                transition_in_song_id + 1]

            snippets.append(
                SongSnippet(
                    self.audio_segment,
                    snippet_id,
                    pre_transition_genre,
                    post_transition_genre,
                    snippet_start_timestamp,
                    transition_timestamp,
                    snippet_end_timestamp))

        return snippets


    def get_end_to_end_snippet(self, transition_timestamp: int):
        return SongSnippet(
            self.audio_segment,
            None,
            None,
            None,
            0,
            transition_timestamp,
            len(self.audio_segment)
        )



class SongDatabase:
    def __init__(self) -> None:
        datafiles = Path("./tests/data/")

        self.song_database = {
            "tsunami": Song(Path(datafiles / "tsunami.mp3"), Path(datafiles / "tsunami.txt")),
            "shot-me-down": Song(Path(datafiles / "shot-me-down.mp3"), Path(datafiles / "shot-me-down.txt")),
            "animals": Song(Path(datafiles / "animals.mp3"), Path(datafiles / "animals.txt")),
            "requiem-for-a-tower": Song(Path(datafiles / "requiem-for-a-tower.mp3"), Path(datafiles / "requiem-for-a-tower.txt")),
            "drink-up-me-hearties": Song(Path(datafiles / "drink-up-me-hearties.mp3"), Path(datafiles / "drink-up-me-hearties.txt")),
            "music": Song(Path(datafiles / "music.mp3"), Path(datafiles / "music.txt")),
            "river-flows-in-you": Song(Path(datafiles / "river-flows-in-you.mp3"), Path(datafiles / "river-flows-in-you.txt"))
        }
        
        self.snippets_by_transition_type = {
            "trafficLight": self.song_database["river-flows-in-you"].get_end_to_end_snippet(5_000),
            "highwayEntrance": self.song_database["shot-me-down"].get_full_snippets_by_genres("low", "high").pop(),
            "tunnelEntrance": self.song_database["animals"].get_full_snippets_by_genres("low", "high").pop(),
            "tunnelExit": self.song_database["drink-up-me-hearties"].get_full_snippets_by_genres("low", "high").pop(),
            "highwayJunction": self.song_database["drink-up-me-hearties"].get_full_snippets_by_genres("crescendo", "high2").pop(),
            "speedLimitRevocation": self.song_database["requiem-for-a-tower"].get_full_snippets_by_genres("low", "high").pop(),
            "highwayExit": self.song_database["river-flows-in-you"].get_end_to_end_snippet(25_000),
        }


    def get_snippet_by_transition_type(self, transition_type) -> SongSnippet:
        assert transition_type in self.snippets_by_transition_type
        
        snippet = self.snippets_by_transition_type[transition_type]
        
        return snippet