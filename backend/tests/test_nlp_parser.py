from app.nlp_parser import parse_text


def test_stated_distance_is_observed_not_inferred():
    result = parse_text("Drove 12km to work and had a vegetarian lunch")
    assert result.commute_mode == "car"
    assert result.commute_distance_km == 12
    assert result.diet_type == "vegetarian"
    assert "commute" not in result.inferred_fields


def test_mode_without_distance_is_inferred_with_a_typical_assumption():
    result = parse_text("Took the bus today")
    assert result.commute_mode == "bus"
    assert result.commute_distance_km == 10.0
    assert "commute" in result.inferred_fields


def test_wfh_implies_zero_distance_and_is_not_inferred():
    result = parse_text("Worked from home all day")
    assert result.commute_mode == "wfh"
    assert result.commute_distance_km == 0.0
    assert "commute" not in result.inferred_fields


def test_energy_kwh_is_parsed():
    result = parse_text("Used about 6.5 kwh of electricity")
    assert result.energy_kwh == 6.5


def test_yesterday_shifts_the_date_back_one_day():
    from datetime import date, timedelta

    today = date(2026, 9, 14)
    result = parse_text("Cycled yesterday", today=today)
    assert result.date == today - timedelta(days=1)


def test_receipt_channel_converts_fuel_litres_to_distance():
    result = parse_text("FUEL STATION\n5.2 L PETROL\nTOTAL RS 550", channel="receipt")
    assert result.commute_mode == "car"
    assert result.commute_distance_km == 78.0  # 5.2 * 15
    assert "commute" in result.inferred_fields


def test_receipt_channel_infers_diet_from_meat_items():
    result = parse_text("GROCERY MART\nCHICKEN 1KG\nRICE 2KG", channel="receipt")
    assert result.diet_type == "meat_heavy"
    assert "food" in result.inferred_fields
