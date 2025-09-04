from dataclasses import dataclass


@dataclass
class SkillJson:
    """Schema-aligned representation of a skill or spell."""

    name: str
    type: str
    function: str
    target: str = "victim"
    lag: int = 0
