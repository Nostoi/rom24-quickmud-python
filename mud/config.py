import os
from dotenv import load_dotenv

load_dotenv()

# Configuration for servers
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mud.db")
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")

# Comma separated list of allowed CORS origins
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")]

# ----- ROM tick cadence (PULSE constants) -----
# ROM defines PULSE_PER_SECOND=4 and PULSE_TICK=60*PULSE_PER_SECOND (see src/merc.h)
# Keep these values here so engine code can reference parity timings.
PULSE_PER_SECOND: int = 4

def get_pulse_tick() -> int:
    """Return pulses per game tick hour (ROM PULSE_TICK).

    Matches ROM's PULSE_TICK = 60 * PULSE_PER_SECOND.
    """
    scale = max(1, int(os.getenv("TIME_SCALE", os.getenv("MUD_TIME_SCALE", "1")) or 1))
    # Allow in-test overrides via module variable as well
    try:
        from mud import config as _cfg  # local import to avoid cycles
        scale = max(scale, int(getattr(_cfg, "TIME_SCALE", 1)))
    except Exception:
        pass
    base = 60 * PULSE_PER_SECOND
    # Ensure at least 1 pulse per tick when scaled up
    return max(1, base // scale)

# Feature flags
COMBAT_USE_THAC0: bool = False

# Optional test-only time scaling (1 = real ROM cadence)
TIME_SCALE: int = 1
