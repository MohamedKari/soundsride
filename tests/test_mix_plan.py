import os
from pathlib import Path

import pytest

from soundsride.song import Song # pylint: disable=import-error

from soundsride.mix_plan import ( # pylint: disable=import-error
    MixPlan, 
    TransitionSpec, 
    SnippetStartEvent,
    SnippetEndEvent,
    GenreTransitionEvent,
    GenrePhase
)

from soundsride.mix_plan import MixPlanViz # pylint: disable=import-error

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")

def get_nonoverlapping_mix_plan(datafiles):
    audio_file = Path(datafiles / "underground.mp3")
    metadata_file = Path(datafiles / "underground.txt")
    transition_spec = TransitionSpec.from_spec_file(Path(datafiles / "transition_spec_01.txt"))

    song = Song(audio_file, metadata_file)

    mix_plan = MixPlan()
    mix_plan.add_snippet_transition(
        song.get_full_snippets_by_genres("calm", "long_crescendo").pop(), 
        100_000
    )

    mix_plan.add_snippet_transition(
        song.get_full_snippets_by_genres("powerful", "halftime").pop(), 
        150_000
    )
    
    return mix_plan, transition_spec


def get_overlapping_mix_plan(datafiles):
    audio_file = Path(datafiles / "underground.mp3")
    metadata_file = Path(datafiles / "underground.txt")
    
    song = Song(audio_file, metadata_file)

    mix_plan = MixPlan()

    # TESTS: Inverted snippet transition adding
    # TESTS: Next snippet starts before the current song's genre transition
    mix_plan.add_snippet_transition(
        song.get_full_snippets_by_genres("calm", "long_crescendo").pop(), 
        50_000
    )

    mix_plan.add_snippet_transition(
        song.get_full_snippets_by_genres("powerful", "halftime").pop(), 
        20_000
    )

    # TESTS: Pause
    mix_plan.add_snippet_transition(
        song.get_full_snippets_by_genres("calm", "long_crescendo").pop(), 
        130_000
    )

    # TESTS: Next snippet starts after the current song's genre transition
    mix_plan.add_snippet_transition(
        song.get_full_snippets_by_genres("halftime", "long_crescendo").pop(), 
        165_000
    )
    
    return mix_plan



@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, "underground.mp3"),
    os.path.join(FIXTURE_DIR, "underground.txt"),
    os.path.join(FIXTURE_DIR, "transition_spec_01.txt"))
def test_mix_plan_creation(datafiles):
    mix_plan, transition_spec = get_nonoverlapping_mix_plan(datafiles)

    assert mix_plan.to_list() == [
        SnippetStartEvent(56_000, 1, 0),
        GenrePhase("calm", 56_000, 100_000),
        GenreTransitionEvent(100_000, 1, 44_000, "calm", "long_crescendo"),
        GenrePhase("long_crescendo", 100_000, 120_000),
        SnippetEndEvent(120_000, 1, 64_000),

        SnippetStartEvent(133_000, 9, 156_000),
        GenrePhase("powerful", 133_000, 150_000),
        GenreTransitionEvent(150_000, 9, 173_000, "powerful", "halftime"),
        GenrePhase("halftime", 150_000, 174_000),
        SnippetEndEvent(174_000, 9, 197_000),
    ]

    mix_plan.print_to_console()   
    

@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, "underground.mp3"),
    os.path.join(FIXTURE_DIR, "underground.txt"),
    os.path.join(FIXTURE_DIR, "transition_spec_01.txt"))
def test_mix_plan_viz(datafiles):
    mix_plan, transition_spec = get_nonoverlapping_mix_plan(datafiles)

    print(transition_spec.genre_transitions)
    
    mix_plan_viz = MixPlanViz()
    
    mix_plan_viz.viz_mix_plan(mix_plan)
    mix_plan_viz.viz_transition_spec(transition_spec)
    mix_plan_viz.viz_segment(mix_plan.to_audio_segment())
    
    mix_plan_viz.show()


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, "underground.mp3"),
    os.path.join(FIXTURE_DIR, "underground.txt"))
def test_overlap_zones(datafiles):
    mix_plan = get_overlapping_mix_plan(datafiles)
    mix_plan_viz = MixPlanViz()
    mix_plan_viz.viz_mix_plan(mix_plan)
    
    overlap_zones = mix_plan._get_overlap_zones()
    
    assert len(overlap_zones) == len(mix_plan.scheduled_snippets) - 1
    assert overlap_zones[0] == (20_000, 44_000)
    assert overlap_zones[1] is None
    assert overlap_zones[2] == (141_000, 150_000)

    mix_plan_viz.viz_segment(mix_plan.to_audio_segment())
    mix_plan_viz.show()


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, "underground.mp3"),
    os.path.join(FIXTURE_DIR, "underground.txt"))
def test_hard_transition_computation(datafiles):

    mix_plan = get_overlapping_mix_plan(datafiles)
    mix_plan_viz = MixPlanViz()
    mix_plan_viz.viz_mix_plan(mix_plan)

    mix_plan.set_snippet_transitions(transition_type="cut")

    scheduled_snippets = mix_plan.scheduled_snippets

    assert len(scheduled_snippets) == 4

    assert scheduled_snippets[0]._fade_in_min == None
    assert scheduled_snippets[0]._fade_in_max == None
    assert scheduled_snippets[0]._fade_out_min == 32_000
    assert scheduled_snippets[0]._fade_out_max == 32_000

    assert scheduled_snippets[1]._fade_in_min == 32_000
    assert scheduled_snippets[1]._fade_in_max == 32_000
    assert scheduled_snippets[1]._fade_out_min == None
    assert scheduled_snippets[1]._fade_out_max == None

    assert scheduled_snippets[2]._fade_in_min == None
    assert scheduled_snippets[2]._fade_in_max == None
    assert scheduled_snippets[2]._fade_out_min == 145_500
    assert scheduled_snippets[2]._fade_out_max == 145_500

    assert scheduled_snippets[3]._fade_in_min == 145_500
    assert scheduled_snippets[3]._fade_in_max == 145_500
    assert scheduled_snippets[3]._fade_out_min == None
    assert scheduled_snippets[3]._fade_out_max == None
    
    mix_plan_viz.viz_segment(mix_plan.to_audio_segment())
    mix_plan_viz.show()

@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, "underground.mp3"),
    os.path.join(FIXTURE_DIR, "underground.txt"))
def test_crossfade_transition_computation(datafiles):

    mix_plan = get_overlapping_mix_plan(datafiles)
    mix_plan_viz = MixPlanViz()
    
    mix_plan.set_snippet_transitions(transition_type="crossfade")
    mix_plan_viz.viz_mix_plan(mix_plan)

    scheduled_snippets = mix_plan.scheduled_snippets

    assert len(scheduled_snippets) == 4

    assert scheduled_snippets[0]._fade_in_min == None
    assert scheduled_snippets[0]._fade_in_max == None
    assert scheduled_snippets[0]._fade_out_min == 41_000
    assert scheduled_snippets[0]._fade_out_max == 44_000

    assert scheduled_snippets[1]._fade_in_min == 41_000
    assert scheduled_snippets[1]._fade_in_max == 44_000
    assert scheduled_snippets[1]._fade_out_min == None
    assert scheduled_snippets[1]._fade_out_max == None

    assert scheduled_snippets[2]._fade_in_min == None
    assert scheduled_snippets[2]._fade_in_max == None
    assert scheduled_snippets[2]._fade_out_min == 147_000
    assert scheduled_snippets[2]._fade_out_max == 150_000

    assert scheduled_snippets[3]._fade_in_min == 147_000
    assert scheduled_snippets[3]._fade_in_max == 150_000
    assert scheduled_snippets[3]._fade_out_min == None
    assert scheduled_snippets[3]._fade_out_max == None
    
    mix_plan_viz.viz_segment(mix_plan.to_audio_segment())
    mix_plan_viz.show()

@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, "underground.mp3"),
    os.path.join(FIXTURE_DIR, "underground.txt"))
def test_negative_start(datafiles):

    audio_file = Path(datafiles / "underground.mp3")
    metadata_file = Path(datafiles / "underground.txt")
    
    song = Song(audio_file, metadata_file)

    mix_plan = MixPlan()

    mix_plan.add_snippet_transition(
        song.get_full_snippets_by_genres("calm", "long_crescendo").pop(), 
        10_000,
        None,
        "OVERLAY"
    )

    def verify_assertions(mix_plan: MixPlan):
        assert mix_plan.scheduled_snippets[0].get_earliest_start() == 0
        assert mix_plan.scheduled_snippets[0].get_scheduled_start() == 0
        assert mix_plan.scheduled_snippets[0].get_scheduled_transition()  == 10_000
        assert mix_plan.scheduled_snippets[0].get_scheduled_end() == 30_000
        assert mix_plan.get_length() == 30_000

    verify_assertions(mix_plan)

    mix_plan.set_snippet_transitions()

    verify_assertions(mix_plan)


    mix_plan.print_to_console()

    mix_plan_viz = MixPlanViz()
    mix_plan_viz.viz_mix_plan(mix_plan)


    mix_plan.set_snippet_transitions()

    mix_plan_viz.viz_segment(mix_plan.to_audio_segment())

    mix_plan_viz.show()