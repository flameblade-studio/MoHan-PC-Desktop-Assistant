from __future__ import annotations

lazy import sys
lazy from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

lazy from scene_semantics import LocalSceneInterpreter
lazy from vision_domain import (
    BoundingBox,
    IdentityObservation,
    IdentityState,
    ObjectDetection,
)


def detection(label: str) -> ObjectDetection:
    return ObjectDetection(label, 0.90, BoundingBox(0, 0, 10, 10))


def run() -> None:
    interpreter = LocalSceneInterpreter()
    owner = IdentityObservation(IdentityState.RECOGNIZED, "1", "Owner", 0.9)
    drinking = interpreter.interpret(owner, (detection("person"), detection("cup")))
    assert drinking.activities == ("possible_drinking",)
    assert drinking.uncertainty == ("drinking_not_confirmed",)
    reading = interpreter.interpret(owner, (detection("person"), detection("book")))
    assert reading.activities == ("possible_reading",)
    assert reading.uncertainty == ("reading_not_confirmed",)
    computer = interpreter.interpret(owner, (detection("laptop"),))
    assert computer.activities == ("at_computer",)
    low_confidence = ObjectDetection("cup", 0.44, BoundingBox(0, 0, 10, 10))
    unsupported = interpreter.interpret(owner, (detection("person"), low_confidence))
    assert unsupported.activities == ()
    assert unsupported.uncertainty == ()
    unknown = IdentityObservation(IdentityState.UNKNOWN)
    observed = interpreter.interpret(unknown, (detection("person"), detection("book")))
    assert observed.identity.state is IdentityState.UNKNOWN
    assert observed.activities == ("possible_reading",)
    assert observed.uncertainty == ("reading_not_confirmed",)


if __name__ == "__main__":
    run()
    print("SCENE_SEMANTICS_OK")
