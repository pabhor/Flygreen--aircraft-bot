import pytest

from models import AircraftCategory


def test_catalog_loaded_with_source_urls(catalog):
    assert len(catalog.aircraft) == 21
    assert all(a.source_url == "https://www.flygreen.co/aircraft-guide" for a in catalog.aircraft)
    assert catalog.max_capacity == 14


@pytest.mark.parametrize("pax", range(1, 20))
def test_never_returns_model_below_passenger_count(catalog, pax):
    for a in catalog.models_that_fit(pax):
        assert a.passenger_capacity >= pax
    for cat in AircraftCategory:
        for a in catalog.example_models(pax, cat):
            assert a.passenger_capacity >= pax


def test_suitable_categories_by_capacity(catalog):
    assert catalog.suitable_categories(5) == list(AircraftCategory)
    assert catalog.suitable_categories(8) == [AircraftCategory.MID_SIZE_JET,
                                              AircraftCategory.SUPER_MID_SIZE_JET,
                                              AircraftCategory.HEAVY_JET]
    assert catalog.suitable_categories(10) == [AircraftCategory.HEAVY_JET]
    assert catalog.suitable_categories(15) == []


def test_light_jet_at_seven_excludes_six_seaters(catalog):
    names = {a.model_name for a in catalog.models_that_fit(7, AircraftCategory.LIGHT_JET)}
    assert names == {"Phenom 300", "Hawker 400XP"}


def test_example_models_limited_and_closest_fit_first(catalog):
    models = catalog.example_models(10, AircraftCategory.HEAVY_JET)
    assert len(models) == 2
    assert models[0].model_name == "Challenger 604"  # capacity 10 = closest fit


def test_invalid_passengers_raises(catalog):
    with pytest.raises(ValueError):
        catalog.models_that_fit(0)
