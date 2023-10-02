import shutil
from concurrent.futures import ThreadPoolExecutor, thread
import logging
from pathlib import Path
from soundsride.service.soundsride_service_pb2 import UpdateTransitionSpecRequest
import time
from numpy import absolute, select
import threading
import traceback

from pydub.audio_segment import AudioSegment
import cv2

from .song import SongDatabase, SongSnippet
from .mix_plan import TransitionSpec, MixPlan, MixPlanViz

from .canvas.transition_spec_canvas import TransitionCanvas 
from .viz_player import VizPlayer
from .consolidator import SerialConsolidator, UpdatingStrategyDetection

def get_millis() -> int:
    return int(time.time() * 1000)

class AppModel:
    transition_spec = None
    mix_plan_fig = None
    segment = None

    sample_position = None



    updated_model = False

class SoundsRideSession:
    
    def __init__(self, app_model: AppModel, session_log_id: str = None) -> None:
        self.app_model = app_model
        self.session_origin = None
        self.session_log_id = session_log_id
        self.transition_spec_canvas = TransitionCanvas()
        self.transition_consolidator = SerialConsolidator(UpdatingStrategyDetection(1050, 15_000))
        self.viz_player = VizPlayer()
        # self.viz_player.monitor_marker_async()
        self.latest_update = None
        
        self.last_mix_plan = None

        self.lock = threading.Lock()

        self.song_database = SongDatabase()

        self.viz_threadpool = ThreadPoolExecutor(3)

        
    def schedule_mix_plan(self, transition_spec: TransitionSpec, only_after_timestamp: int) -> MixPlan:
        mix_plan = MixPlan()

        # TODO: Don't schedule transition for the past

        if self.last_mix_plan:
            last_scheduled_snippet = self.last_mix_plan.get_last_scheduled_snippet_before_timestamp(only_after_timestamp)

            if last_scheduled_snippet:
                mix_plan._scheduled_snippets.append(last_scheduled_snippet)


        i = 0
        for transition_id, (left_genre, timestamp, right_genre) in zip(transition_spec.transition_ids, transition_spec.iterate_transitions(absolute=True)):
            logging.getLogger(__name__).debug("Scheduling: from %s at %s to %s", left_genre, timestamp, right_genre)
            # snippet = self.song_database.get_snippet_by_transition_id(int(transition_id))
            
            if timestamp < only_after_timestamp: 
                continue

            if i == 3:
                break

            i += 1

            snippet = self.song_database.get_snippet_by_transition_type(right_genre)

            if right_genre == "highwayExit":
                transition_mode = "SLOW"
            else:
                # transition_mode = "MEDIUM"
                transition_mode = "EARLY" # it is a bit annoying if snippets start in the middle

            assert isinstance(snippet, SongSnippet)
            mix_plan.add_snippet_transition(
                snippet,
                timestamp,
                transition_mode)

        return mix_plan  

    def update_mix_plan(self, request: UpdateTransitionSpecRequest, request_log_id: str):
        if self.lock.locked():
            logging.getLogger(__name__).warning("DROPPED FRAME!")
            return 

        # Currently, we drop frames all the time
        # Must speed up this by a factor of 10
        # - Render off-thread
        # - Only export audio for the next 10 seconds now or pull audio and pre-fetch off-thread

        with self.lock:     

            next_transistion_spec = TransitionSpec.from_spec_protobuf(request, absolute_start_timestamp=None, negative_ett_handling="skip")
            print("next_transistion_spec", next_transistion_spec)

            if not next_transistion_spec.genre_transitions:
                return
            
            # First time playback 
            if not self.session_origin:
                # We must set the session_origin only at the same time (or just shortly before) first playback,
                # otherwise playback_time and session_time are shifted
                self.session_origin = get_millis()

            now_in_ms = get_millis() - self.session_origin

            next_transistion_spec.absolute_start_timestamp = now_in_ms

            updating_strategy = self.transition_consolidator.update(now_in_ms, next_transistion_spec)
            logging.getLogger(__name__).info("Strategy is %s", (updating_strategy and updating_strategy.name) or None)

            self.transition_consolidator.print_to_console()
            consolidated_transition_spec = self.transition_consolidator.get()


            if (updating_strategy and updating_strategy.action_required) or (updating_strategy is None):
                
                logging.getLogger(__name__).info("Scheduling mix_plan from transition_spec %s", next_transistion_spec)
                mix_plan = self.schedule_mix_plan(consolidated_transition_spec, now_in_ms)

                logging.getLogger(__name__).info("Setting snippets from transition_spec")
                mix_plan.set_snippet_transitions(transition_type="crossfade")

                logging.getLogger(__name__).info("Rendering signal.")
                segment = mix_plan.to_audio_segment() # TODO: ONLY LOAD NEXT CHUNK, QUEUE EVERYTHING ELSE
                self.last_mix_plan = mix_plan

                logging.getLogger(__name__).info("Updating signal.") 
                self.viz_player.swap_segment(segment)
              

            def viz():
                if updating_strategy and updating_strategy.action_required:
                    self.transition_spec_canvas.draw_segment(segment)
                    # self.transition_spec_canvas.draw_snippets(mix_plan.scheduled_snippets)
                    
                try:
                    logging.getLogger(__name__).info("Setting consolidated spec...")
                    self.transition_spec_canvas.set_consolidated_transition_spec(consolidated_transition_spec, updating_strategy)

                    logging.getLogger(__name__).info("Drawing transition specs...")
                    self.transition_spec_canvas.draw_transition_spec(next_transistion_spec)

                    logging.getLogger(__name__).info("Setting marker...")
                    self.transition_spec_canvas.set_marker(now_in_ms)

                    logging.getLogger(__name__).info("Setting waveform marker...")
                    self.transition_spec_canvas.set_waveform_marker(self.viz_player.playback_state.played_milliseconds)
                                    
                    logging.getLogger(__name__).info("Saving to waveform marker...")
                    self.transition_spec_canvas.save("canvas.jpg")

                    if request_log_id:
                        shutil.copyfile("canvas.jpg", f"log/{self.session_log_id}/{request_log_id}.jpg")
            
                except Exception as e:
                    print(traceback.format_exc())

            self.viz_threadpool.submit(viz)

            logging.getLogger(__name__).info("Drawing finished!")

            logging.getLogger(__name__).info("Done.") 