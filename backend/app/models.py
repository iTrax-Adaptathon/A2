from sqlalchemy import Column, Date, Float, Integer, String

from .database import Base


class LogEntry(Base):
    """
    One row per day. Every lifestyle field is nullable on purpose --
    users log irregularly and rarely fill in everything, and the
    estimator (see estimator.py) is designed to cope with that instead
    of assuming missing == zero.
    """

    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)

    commute_mode = Column(String, nullable=True)          # key into region's commute_kg_per_km
    commute_distance_km = Column(Float, nullable=True)

    diet_type = Column(String, nullable=True)              # key into DIET_FACTORS_KG_PER_DAY

    energy_kwh = Column(Float, nullable=True)               # direct meter reading, if known
    energy_level = Column(String, nullable=True)            # low/medium/high fallback

    flight_km = Column(Float, nullable=True)
    flight_haul = Column(String, nullable=True)              # "short" | "long"

    shopping_level = Column(String, nullable=True)           # low/medium/high

    region = Column(String, nullable=False, default="IN")   # which emission-factor profile was used

    # Multi-modal logging provenance: which input channel produced this row.
    channel = Column(String, nullable=False, default="form")  # form | natural_language | voice | receipt

    # Comma-separated subset of {"commute","food","energy"} that the
    # channel had to *infer* a gap for (e.g. NL logging said "drove to
    # work" with no distance) rather than an exact figure -- read back
    # as entry.inferred_fields (a set) via the property below.
    inferred_fields_raw = Column(String, nullable=True)

    notes = Column(String, nullable=True)

    @property
    def inferred_fields(self):
        if not self.inferred_fields_raw:
            return set()
        return set(self.inferred_fields_raw.split(","))

    @inferred_fields.setter
    def inferred_fields(self, value):
        self.inferred_fields_raw = ",".join(sorted(value)) if value else None


class Budget(Base):
    """
    A singleton row -- setting a new budget replaces the old one rather
    than keeping history, so "current budget" is always just the one
    row here. Streak/status math (see budget.py) only looks at days
    on/after `created_date`, so replacing the budget naturally resets
    progress rather than retroactively judging days against a target
    that didn't exist yet.
    """

    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    target_kg_per_day = Column(Float, nullable=False)
    created_date = Column(Date, nullable=False)
