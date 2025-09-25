from mud.models.constants import DefenseBit, ImmFlag, ResFlag, VulnFlag


def test_imm_res_vuln_intflags_match_defense_bits():
    # Spot-check a few letters across the range
    assert int(ImmFlag.FIRE) == int(DefenseBit.FIRE)
    assert int(ResFlag.COLD) == int(DefenseBit.COLD)
    assert int(VulnFlag.LIGHTNING) == int(DefenseBit.LIGHTNING)
    assert int(ImmFlag.SILVER) == int(DefenseBit.SILVER)
    assert int(ResFlag.IRON) == int(DefenseBit.IRON)


def test_imm_res_vuln_flags_are_bitwise_compatible():
    # Ensure bitwise OR yields same combined mask as DefenseBit
    imm = int(ImmFlag.FIRE | ImmFlag.COLD)
    ref = int(DefenseBit.FIRE) | int(DefenseBit.COLD)
    assert imm == ref
