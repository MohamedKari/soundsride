from typing import Tuple, Optional

from rich import print

from .mix_plan import ScheduledSnippet, TransitionSpec

class TransitionConsolidator:
    def __init__(self):
        self.transition_spec_history = None
        self.consolidated_transition_spec = None
        

    def update(self, next_transition_spec):
        raise NotImplementedError()

    def get(self) -> TransitionSpec:
        return self.consolidated_transition_spec

class ThrottleConsolidator(TransitionConsolidator):

    def __init__(self):
        super().__init__()
        self.counter = 0
        self.throttle = 1

    def update(self, next_transition_spec):
        if self.counter % self.throttle == 0: 
            print("UPDATING")
            self.consolidated_transition_spec = next_transition_spec
        else:
            print("THROTTLING")

        self.counter += 1


class UpdatingStrategy():
    def __init__(
            self, 
            name: str = None,
            diff_current_to_planned: int = None,  
            diff_current_to_actual: int = None, 
            diff_planned_to_actual: int = None, 
            action_required: bool = None) -> None:
        
        self.name = name
        self.diff_current_to_planned = diff_current_to_planned
        self.diff_current_to_actual = diff_current_to_actual
        self.diff_planned_to_actual = diff_planned_to_actual
        self.action_required = action_required

    
    def __call__(
            self, 
            name: str = None,
            diff_current_to_planned: int = None,  
            diff_current_to_actual: int = None, 
            diff_planned_to_actual: int = None, 
            action_required: bool = None):
        
        self.name = name or self.name
        self.diff_current_to_planned = diff_current_to_planned or self.diff_current_to_planned
        self.diff_current_to_actual = diff_current_to_actual or self.diff_current_to_actual
        self.diff_planned_to_actual = diff_planned_to_actual or self.diff_planned_to_actual 
        self.action_required = action_required or self.action_required

        return self

    def __repr__(self) -> str:
        return f"{self.name}: current_to_planned {self.diff_current_to_planned}, current_to_actual {self.diff_current_to_actual}, planned_to_actual {self.diff_planned_to_actual}"

class UpdatingStrategyDetection:
    
    def __init__(self, deviation_tolerance: int = 0, hot_zone_entrance: int = float("inf")) -> None:
        """
        args:
        - `deviation_tolerance` (`int`): 
            Sets the threshold in ms up to which it is acceptable to misalign actual and planned at the advantage of avoiding a setup. 
        - `hot_zone_entrance` (`int`): 
            Sets the time frame in ms enclosing the next transition in which . 
            Increasing this will update the planned time stamp earlier.
            The better we can guess the time distance to the next transition, the earlier we can update, that is the higher we can set this value. 
            However, if we are not good in estimating the time distance, we will need to redapt our estimations later.
            In general, the better we can guess the higher we can set this. The higher we set this, the more often we will need to readapt the transition spec to new information.


        By default, `deviation_tolerance` is set to zero and `hot_zone_entrance` is set to `float("inf")`, that is we are always in a hot zone and not accepting any mislignments. 
        This means that we will always update to the actual timestamp of the next transition, resulting in permament updates of the next timestamp.
        """
        self.deviation_tolerance = deviation_tolerance
        self.hot_zone_entrance = hot_zone_entrance

    def detect(
            self, 
            current_timestamp: int,
            next_planned_transition_id: str, 
            next_planned_transition_timestamp_absolute: str,
            next_actual_transition_id: str, 
            next_actual_transition_timestamp_absolute: int
            ) -> UpdatingStrategy:

        # TODO: detect FreeRides (that is being in a post-part of a snippet) using the mixplan
        # TODO: include climax duration
        # TODO: Insert PointOfNoReturnCrossed using a safe ClimaxDuration preceding the transition
        # TODO: Detect edging = continuously delaying (or probably do this in the localization client instead)

        DEVIATION_TOLERANCE = self.deviation_tolerance
        HOT_ZONE_ENTRANCE = self.hot_zone_entrance

        if not next_planned_transition_id and not next_actual_transition_id:
            return UpdatingStrategy(name="Idling", action_required=False)
           
        if next_planned_transition_id and not next_actual_transition_id:
            # We planned something, but nothing is upcoming anymore
            # Probably we passed the final transition 
            # (We could use a Kalman-like approach to make predictions and compare those to be certain on this but let's not overengineer it)
            return UpdatingStrategy(name="PassedFinalTransition", action_required=True)
       
        # If we are here, that means we do have upcoming transitions
        # First, let's get the next one
        
        if not next_planned_transition_id and next_actual_transition_id:
            return UpdatingStrategy(name="Start", action_required=True)
        
        if next_planned_transition_id and next_actual_transition_id:
            # Main line case
            pass


        if next_planned_transition_id == next_actual_transition_id:
            diff_current_to_planned = next_planned_transition_timestamp_absolute - current_timestamp
            diff_current_to_actual = next_actual_transition_timestamp_absolute - current_timestamp
            diff_planned_to_actual = next_actual_transition_timestamp_absolute - next_planned_transition_timestamp_absolute

            updating_strategy = UpdatingStrategy(
                diff_current_to_planned=diff_current_to_planned, 
                diff_current_to_actual=diff_current_to_actual, 
                diff_planned_to_actual=diff_planned_to_actual)

            # Planned and actual distance beyond hot zone
            if   diff_current_to_actual >= HOT_ZONE_ENTRANCE and                                 diff_current_to_planned >= HOT_ZONE_ENTRANCE and                                  abs(diff_planned_to_actual) >=    DEVIATION_TOLERANCE:
                return updating_strategy(name="Temporise", action_required=False)
            elif diff_current_to_actual >= HOT_ZONE_ENTRANCE and                                 diff_current_to_planned >= HOT_ZONE_ENTRANCE and                                  abs(diff_planned_to_actual) <=    DEVIATION_TOLERANCE:
                return updating_strategy(name="Temporise", action_required=False)

            # Planned and actual distance in hot zone
            elif diff_current_to_actual <= HOT_ZONE_ENTRANCE and diff_current_to_actual >= 0 and diff_current_to_planned <= HOT_ZONE_ENTRANCE and diff_current_to_planned >= 0 and abs(diff_planned_to_actual) <=    DEVIATION_TOLERANCE:
                return updating_strategy(name="NeglectMisalignment", action_required=False)
            elif diff_current_to_actual <= HOT_ZONE_ENTRANCE and diff_current_to_actual >= 0 and diff_current_to_planned <= HOT_ZONE_ENTRANCE and diff_current_to_planned >= 0 and     diff_planned_to_actual  >=    DEVIATION_TOLERANCE:
                return updating_strategy(name="Delay", action_required=True)
            elif diff_current_to_actual <= HOT_ZONE_ENTRANCE and diff_current_to_actual >= 0 and diff_current_to_planned <= HOT_ZONE_ENTRANCE and diff_current_to_planned >= 0 and     diff_planned_to_actual  <=  - DEVIATION_TOLERANCE:
                return updating_strategy(name="Accelerate", action_required=True)

            # Actual distance beyond hot zone, planned distance in hot zone
            elif diff_current_to_actual >= HOT_ZONE_ENTRANCE and                                 diff_current_to_planned <= HOT_ZONE_ENTRANCE and diff_current_to_planned >= 0 and abs(diff_planned_to_actual) <=    DEVIATION_TOLERANCE: 
                return updating_strategy(name="NeglectMisalignment", action_required=False)
            elif diff_current_to_actual >= HOT_ZONE_ENTRANCE and                                 diff_current_to_planned <= HOT_ZONE_ENTRANCE and diff_current_to_planned >= 0 and     diff_planned_to_actual  >=    DEVIATION_TOLERANCE: 
                return updating_strategy(name="Delay", action_required=True)

            # Actual distance in hot zone, planned distance beyond hot zone
            elif diff_current_to_actual <= HOT_ZONE_ENTRANCE and                                 diff_current_to_planned >= HOT_ZONE_ENTRANCE and diff_current_to_planned >= 0 and abs(diff_planned_to_actual) <=    DEVIATION_TOLERANCE: 
                return updating_strategy(name="NeglectMisalignment", action_required=False)
            elif diff_current_to_actual <= HOT_ZONE_ENTRANCE and                                 diff_current_to_planned >= HOT_ZONE_ENTRANCE and diff_current_to_planned >= 0 and     diff_planned_to_actual  <=  - DEVIATION_TOLERANCE: 
                return updating_strategy(name="Accelerate", action_required=True)

             # Planned transition already passed, but actual transition is still upcoming 
            elif                                                 diff_current_to_actual >= 0 and                                                  diff_current_to_planned <= 0 and     diff_planned_to_actual  <=   DEVIATION_TOLERANCE: 
                return updating_strategy(name="EndureMissedTransition", action_required=False)
            elif                                                 diff_current_to_actual >= 0 and                                                  diff_current_to_planned <= 0 and     diff_planned_to_actual  >=   DEVIATION_TOLERANCE: 
                return updating_strategy(name="RedispatchMissedTransition", action_required=True)

            else:
                 return updating_strategy(name="Undefined")

        else: # next_planned_transition_id != next_actual_transition_id
            return UpdatingStrategy(name="Passed", action_required=True)

        return ""

class SerialConsolidator(TransitionConsolidator):
    
    def __init__(self, updating_strategy_detection: UpdatingStrategyDetection = UpdatingStrategyDetection()):
        super().__init__()

        self.passed_transitions: TransitionSpec = TransitionSpec(
            genre_transitions={},
            transition_ids=[],
            absolute_start_timestamp=0
        )

        self.next_planned_transition_timestamp_absolute: int = None
        self.next_planned_transition_genre: str = None
        self.next_planned_transition_id: str = None

        self.distant_transitions: TransitionSpec = TransitionSpec(
            genre_transitions={},
            transition_ids=[],
            absolute_start_timestamp=0
        ) 

        self.updating_strategy_detection = updating_strategy_detection

        self.latest_strategy = None
    
    def move_next_planned_transition_to_passed_transitions(self):
        self.passed_transitions.genre_transitions[self.next_planned_transition_timestamp_absolute] = self.next_planned_transition_genre
        self.passed_transitions.transition_ids.append(self.next_planned_transition_id)
            
        self.next_planned_transition_id = None
        self.next_planned_transition_genre = None
        self.next_planned_transition_timestamp_absolute = None
    
    def update_distant_transitions(self, next_transition_spec: TransitionSpec):
        self.distant_transitions = TransitionSpec(
                genre_transitions = dict(list(next_transition_spec.genre_transitions.items())[1:]),
                absolute_start_timestamp = next_transition_spec.absolute_start_timestamp,
                transition_ids = next_transition_spec.transition_ids[1:]
        )

    def get_next_actual_transition(self, next_transition_spec: TransitionSpec) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        if not next_transition_spec.genre_transitions:
            return None, None, None
        
        next_actual_transition_id = next_transition_spec.transition_ids[0]
        next_actual_transition_timestamp_absolute = list(next_transition_spec.absolute_genre_transitions().keys())[0]
        next_actual_transition_genre = list(next_transition_spec.genre_transitions.values())[0]
        
        return next_actual_transition_id, next_actual_transition_timestamp_absolute, next_actual_transition_genre
    
    def update_next_planned_transition(self, next_transition_spec: TransitionSpec):
        next_actual_transition_id, next_actual_transition_timestamp_absolute, next_actual_transition_genre = \
            self.get_next_actual_transition(next_transition_spec)

        self.next_planned_transition_timestamp_absolute = next_actual_transition_timestamp_absolute
        self.next_planned_transition_genre = next_actual_transition_genre
        self.next_planned_transition_id = next_actual_transition_id


    def merge_to_full_transition_spec(self) -> TransitionSpec: 
        return TransitionSpec(
            genre_transitions = dict(
                [(timestamp, right_genre) for timestamp, right_genre in self.passed_transitions.absolute_genre_transitions().items()] + \
                [(self.next_planned_transition_timestamp_absolute, self.next_planned_transition_genre) for _ in range(bool(self.next_planned_transition_timestamp_absolute))] + \
                [(timestamp, right_genre) for timestamp, right_genre in self.distant_transitions.absolute_genre_transitions().items()]),
            transition_ids = \
                self.passed_transitions.transition_ids + \
                [self.next_planned_transition_id] + \
                self.distant_transitions.transition_ids,
            absolute_start_timestamp=self.passed_transitions.absolute_start_timestamp
        )
        
    def print_to_console(self):
        output = []
        if self.passed_transitions:
            output.append(f"[white]{self.passed_transitions}[/white]")
       
        if self.next_planned_transition_id:
            output.append(f"[red]{self.next_planned_transition_id}: {self.next_planned_transition_timestamp_absolute} -> {self.next_planned_transition_genre}[/red]")
            
        if self.distant_transitions:
            output.append(f"[blue]{self.distant_transitions}[/blue]")

        output = " | ".join(output)

       

        if self.latest_strategy.name == "Temporise":
            color = "yellow"
        elif self.latest_strategy.name == "Delay":
            color = "purple"
        elif self.latest_strategy.name == "Accelerate":
            color = "medium_purple2"
        elif self.latest_strategy.name == "NeglectMisalignment":
            color = "light_green"
        elif self.latest_strategy.name == "Passed":
            color = "dark_green"
        elif self.latest_strategy.name == "RedispatchMissedTransition":
            color = "gold3"
        elif self.latest_strategy.name == "EndureMissedTransition":
            color = "dark_orange3"
        else:
            color = "red"

        output += f" | [{color}]{self.latest_strategy}[/{color}]"

        print(output)


    def update(self, current_timestamp: int, next_transition_spec: TransitionSpec) -> Optional[UpdatingStrategy]:
        # planned_transition_count = int(bool(self.next_actual_transition_id)) + len(self.distant_transitions.genre_transitions)
        # actual_upcoming_transition_count = len(next_transition_spec.genre_transitions)
        # if abs(planned_transition_count - actual_upcoming_transition_count) > 1:
        #     raise ValueError("Too much changed without supervision!")


        # TODO: Simplify all of the below  by handling empty-list-cases in the functions thus making the if statements unnesseary
        # TODO: Check if order is okay when we pass a transition: if passed: assert distant_transitions.transition_ids[0] == next_actual_transition_id
        # print(f"next_planned_transition_id: {bool(self.next_planned_transition_id)}, next_transition_spec.genre_transitions: {bool(next_transition_spec.genre_transitions)}")

        # Deal with the upcoming transition
        next_actual_transition_id, next_actual_transition_timestamp_absolute, next_actual_transition_genre = \
            self.get_next_actual_transition(next_transition_spec)

        if next_actual_transition_id in self.passed_transitions.genre_transitions:
            return None

        strategy = self.updating_strategy_detection.detect(
            current_timestamp,
            self.next_planned_transition_id,
            self.next_planned_transition_timestamp_absolute,
            next_actual_transition_id,
            next_actual_transition_timestamp_absolute
        )

        self.latest_strategy = strategy


        if strategy.name == "Idling":
            # Nothing planned, nothing upcoming => nothing to do
            return strategy
        
        if strategy.name == "PassedFinalTransition":
            # We planned something, but nothing is upcoming anymore
            # Probably we passed the final transition 
            # (We could use a Kalman-like approach to make predictions and compare those to be certain on this but let's not overengineer it)
            # passed the final transition
            self.move_next_planned_transition_to_passed_transitions()
            return strategy
    
        # If we are here, that means we do have upcoming transitions
        # First, let's get the next one

        
        if strategy.name == "Start":
            # We don't have something planned, so let's plan with the upcoming transition
            self.update_next_planned_transition(next_transition_spec)

            # Copy over distant transitions one to one
            self.update_distant_transitions(next_transition_spec)

            return strategy
        
    


        if self.next_planned_transition_id == next_actual_transition_id:
            # The most recently planned next transition is still the actual next transition
            # All we need to do is update the timestamp (genre cannot change and transition_id didn't change by definition)
            # 
            # However, we need to apply throttling here
            

            # We have something planned and there is something upcoming,
            # so we need to check if we are still in sync
            # Sice this is the last option left, we can as well continue in the main line
            
            if strategy.name == "Delay":
                self.next_planned_transition_timestamp_absolute = next_actual_transition_timestamp_absolute

            if strategy.name == "Accelerate":
                self.next_planned_transition_timestamp_absolute = next_actual_transition_timestamp_absolute

            if strategy.name == "Temporise":
                pass

            if strategy.name == "NeglectMisalignment":
                pass

            if strategy.name == "EndureMissedTransition":
                pass

            if strategy.name == "RedispatchMissedTransition":
                self.next_planned_transition_timestamp_absolute = next_actual_transition_timestamp_absolute
            
            
            self.update_distant_transitions(next_transition_spec)
            return strategy

        # If we are here, we have something planned, something is upcoming, 
        # but the transition we thought would come next is not equal to the next_actual_transition
        #
        # Reasons could be 
        # - that we passed it; in that case the next_transition to the passed
        # - that a new transition was inserted before the planned transition; we could check if our transition id is be found later in the next_transition_spec, but for now, let's not allow the client to insert transitions spontaneously
        # - that it was simply removed form the future; let's not allow the client to do this for now
        #
        # For now, let's assume that we just passed the next_transition
        # We could, of course, make this plausible by employing a Kalman-like prediction-based approach, 
        # but for now, let's just assume we passed it
        self.move_next_planned_transition_to_passed_transitions()
        self.update_next_planned_transition(next_transition_spec)
        self.update_distant_transitions(next_transition_spec)



    def get(self) -> TransitionSpec:
        return self.merge_to_full_transition_spec()
            
