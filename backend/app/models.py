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

    commute_mode = Column(String, nullable=True)          # key into COMMUTE_FACTORS_KG_PER_KM
    commute_distance_km = Column(Float, nullable=True)

    diet_type = Column(String, nullable=True)              # key into DIET_FACTORS_KG_PER_DAY

    energy_kwh = Column(Float, nullable=True)               # direct meter reading, if known
    energy_level = Column(String, nullable=True)            # low/medium/high fallback

    notes = Column(String, nullable=True)
