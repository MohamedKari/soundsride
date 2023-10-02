import time
from pathlib import Path
import json
from typing import Dict
import os

import pytest
from google.protobuf.json_format import ParseDict

from soundsride.mix_plan import TransitionSpec
from soundsride.consolidator import SerialConsolidator, ThrottleConsolidator, UpdatingStrategyDetection
from soundsride.service.soundsride_service_pb2 import (
    UpdateTransitionSpecRequest)

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")

class UpdateSpecRequestLoader:

    def __init__(self, directory_path: str, sleep=False) -> None:
        self._gen = UpdateSpecRequestLoader._generator(sorted(Path(directory_path).glob("*.json")), sleep=sleep)
        self.sleep = sleep

    @staticmethod
    def _generator(filenames, sleep):
        
        start_timestamp = None
        last_offset = 0

        for filename in filenames:
            timestamp = int(Path(filename).stem)
            if not start_timestamp:
                offset = start_timestamp = timestamp
            
            offset = timestamp - start_timestamp

            if sleep:
                time.sleep((offset - last_offset) / 30000)
            
            last_offset = offset

            yield (offset, json.loads(Path(filename).read_text()))


    def __iter__(self):
        return self

    def __next__(self) -> dict:
        return next(self._gen)


# @pytest.mark.skip
def test_consolidator():
    consolidator = SerialConsolidator()

    initial_genre = "low"
       
    test_steps = [
        {
            "new": {
                "current_timestamp": 0,
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "etts":                 [10_000, 20_000, 30_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_000, 20_000, 30_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {
            "new": {
                "current_timestamp": 1000,
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "etts":                 [9_000, 19_000, 29_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_000, 20_000, 30_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {
            "new": {
                "current_timestamp": 2000,
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "etts":                 [8_500, 18_500, 28_500], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 20_500, 30_500], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {
            "new": {
                "current_timestamp": 2000,
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "etts":                 [8_500, 18_500, 28_500], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 20_500, 30_500], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {
            "new": {
                "current_timestamp": 10_000,
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "etts":                 [500, 10_500, 20_500], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 20_500, 30_500], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {
            "new": {
                "current_timestamp": 12_000,
                "transitions": {
                    "transition_ids":       [10, 15], 
                    "etts":                 [7_000, 17_000], 
                    "transition_to_genre":  ["low", "high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 19_000, 29_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {
            "new": {
                "current_timestamp": 19_000,
                "transitions": {
                    "transition_ids":       [10, 15], 
                    "etts":                 [0, 10_000], 
                    "transition_to_genre":  ["low", "high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 19_000, 29_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {
            "new": {
                "current_timestamp": 19_000,
                "transitions": {
                    "transition_ids":       [15], 
                    "etts":                 [10_000], 
                    "transition_to_genre":  ["high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 19_000, 29_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {   # Accelerating next transition
            "new": {
                "current_timestamp": 26_000,
                "transitions": {
                    "transition_ids":       [15], 
                    "etts":                 [1_000], 
                    "transition_to_genre":  ["high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 19_000, 27_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {   # Delaying next transition
            "new": {
                "current_timestamp": 27_000,
                "transitions": {
                    "transition_ids":       [15], 
                    "etts":                 [1_000], 
                    "transition_to_genre":  ["high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 19_000, 28_000], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {   # Delaying next transition again
            "new": {
                "current_timestamp": 28_000,
                "transitions": {
                    "transition_ids":       [15], 
                    "etts":                 [500], 
                    "transition_to_genre":  ["high"]
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 19_000, 28_500], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        },
        {   # Delaying next transition
            "new": {
                "current_timestamp": 29_000,
                "transitions": {
                    "transition_ids":       [], 
                    "etts":                 [], 
                    "transition_to_genre":  []
                }
            }, 
            "updated": {
                "transitions": {
                    "transition_ids":       [5, 10, 15], 
                    "absolute_timestamps":  [10_500, 19_000, 28_500], 
                    "transition_to_genre":  ["high", "low", "high"]
                }
            }
        }
    ]

    consolidator = SerialConsolidator()

    
    for test_step in test_steps:
        current_timestamp = test_step["new"]["current_timestamp"]
        transition_ids = test_step["new"]["transitions"]["transition_ids"]
        genre_transitions = dict([
            (ett, genre)
            for ett, genre 
            in zip(test_step["new"]["transitions"]["etts"], test_step["new"]["transitions"]["transition_to_genre"])])

        new_transition_spec = TransitionSpec(genre_transitions, transition_ids, current_timestamp)

        consolidator.update(current_timestamp, new_transition_spec)
        updated = consolidator.get()

        expected_updated_genre_transition = dict([
            (absolute_timestamp, genre)
            for absolute_timestamp, genre 
            in zip(test_step["updated"]["transitions"]["absolute_timestamps"], test_step["updated"]["transitions"]["transition_to_genre"])])

        assert updated.absolute_genre_transitions() == expected_updated_genre_transition

        
        print(updated)

    return 



# @pytest.mark.skip
@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, "grpc_message_dump/1613557648788/"))
def test_full_trajectory_with_continuous_updates(datafiles):
    loader = UpdateSpecRequestLoader(datafiles, sleep=False)
    consolidator = SerialConsolidator()

    for timestamp, update_spec_request_dict in loader:
        update_spec_request_message = ParseDict(update_spec_request_dict, UpdateTransitionSpecRequest())
        transition_spec = TransitionSpec.from_spec_protobuf(update_spec_request_message, absolute_start_timestamp=timestamp, negative_ett_handling="skip")
        consolidator.update(timestamp, transition_spec)
        consolidator.get()


# @pytest.mark.skip
@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, "grpc_message_dump/1613557648788/"))
def test_full_trajectory_with_cautious_updates(datafiles):
    loader = UpdateSpecRequestLoader(datafiles, sleep=False)
    consolidator = SerialConsolidator(UpdatingStrategyDetection(1000, 10_000))

    for timestamp, update_spec_request_dict in loader:
        update_spec_request_message = ParseDict(update_spec_request_dict, UpdateTransitionSpecRequest())
        transition_spec = TransitionSpec.from_spec_protobuf(update_spec_request_message, absolute_start_timestamp=timestamp, negative_ett_handling="skip")
        consolidator.update(timestamp, transition_spec)
        consolidator.get()
        consolidator.print_to_console()

