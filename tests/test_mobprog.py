from mud.models.mob import MobIndex, MobProgram
from mud import mobprog


def test_speech_trigger_executes_code():
    prog = MobProgram(
        trig_type=int(mobprog.Trigger.SPEECH),
        trig_phrase="hello",
        code="say Hello back!"
    )
    mob = MobIndex(vnum=1, mprogs=[prog])
    results = mobprog.run_prog(
        mob, mobprog.Trigger.SPEECH, phrase="hello there"
    )
    expected = [mobprog.ExecutionResult("say", "Hello back!")]
    assert results == expected


def test_non_matching_phrase_skips_code():
    prog = MobProgram(
        trig_type=int(mobprog.Trigger.SPEECH),
        trig_phrase="bye",
        code="say Bye"
    )
    mob = MobIndex(vnum=1, mprogs=[prog])
    results = mobprog.run_prog(
        mob, mobprog.Trigger.SPEECH, phrase="hello there"
    )
    assert results == []
