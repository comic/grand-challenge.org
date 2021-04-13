import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from grandchallenge.workstation_configs.models import LookUpTable, WindowPreset
from tests.workstation_config_tests.legacy_luts import LEGACY_LUTS, LegacyLUT


@pytest.mark.parametrize(
    "color,valid",
    (
        ("", False),
        ("[]", False),
        ("[1 2 3 4, 5 6 7 8]", True),
        ("[1 2 3 4, 5 6 7 8]\n\n", False),
    ),
)
def test_lut_color_regex(color, valid):
    lut = LookUpTable(color=color)
    err = None

    try:
        lut.clean_fields()
    except ValidationError as e:
        err = e

    assert ("color" in err.error_dict) != valid


@pytest.mark.parametrize("legacy_lut", LEGACY_LUTS)
def test_legacy_lut_conversion(legacy_lut: LegacyLUT):
    lut = LookUpTable(
        color=legacy_lut.lut_color,
        title=legacy_lut.title,
        alpha=legacy_lut.lut_alpha,
        color_invert=legacy_lut.lut_color_invert,
        alpha_invert=legacy_lut.lut_alpha_invert,
        range_min=legacy_lut.lut_range[0],
        range_max=legacy_lut.lut_range[1],
        relative=legacy_lut.lut_relative,
        color_interpolation=legacy_lut.color_interpolation.replace(
            "Interpolate", ""
        ),
        color_interpolation_invert=legacy_lut.color_interpolation_invert.replace(
            "Interpolate", ""
        ),
    )
    lut.full_clean()


@pytest.mark.parametrize(
    "lut",
    (
        LookUpTable(
            title="foo",
            color="[1 2 3 4, 5 6 7 8, 9 10 11 12]",
            alpha="[1 1, 1 1]",
        ),
        LookUpTable(
            title="foo", color="[1 2 3 4, 5 6 7 8]", alpha="[1 1, 1 1, 1 1]"
        ),
        LookUpTable(
            title="foo",
            color="[1 2 3 4, 5 6 7 8]",
            alpha="[1 1, 1 1]",
            color_invert="[1 2 3 4, 5 6 7 8, 9 10 11 12]",
            alpha_invert="[1 1, 1 1]",
        ),
        LookUpTable(
            title="foo",
            color="[1 2 3 4, 5 6 7 8]",
            alpha="[1 1, 1 1]",
            color_invert="[1 2 3 4, 5 6 7 8]",
            alpha_invert="[1 1, 1 1, 1 1]",
        ),
    ),
)
def test_color_alpha_validation(lut):
    lut.clean_fields()
    with pytest.raises(ValidationError):
        lut.full_clean()


window_presets_tests = [
    ({"width": 2000, "center": 0}, True),
    ({"width": 0, "center": 0}, False),
    ({"lower_percentile": 15, "upper_percentile": 85}, True,),
    ({"lower_percentile": 15, "upper_percentile": 15}, False),
    ({"lower_percentile": 15, "upper_percentile": 16}, True),
    ({"width": -2000, "center": 0}, False),
    ({}, False),
    ({"width": 1}, False),
    ({"center": 1}, False),
    ({"lower_percentile": 1}, False),
    ({"upper_percentile": 1}, False),
    ({"width": 1, "lower_percentile": 1}, False),
    ({"center": 1, "lower_percentile": 1}, False),
    ({"width": 1, "upper_percentile": 1}, False),
    ({"center": 1, "upper_percentile": 1}, False),
    ({"lower_percentile": 85, "upper_percentile": 15}, False),
]

ids = [f"{p[0]} -> valid:{p[1]}" for p in window_presets_tests]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "config, expected_valid", window_presets_tests, ids=ids
)
def test_window_presets_db_integrity(config, expected_valid):
    preset = WindowPreset(title="foo", **config)
    if expected_valid:
        preset.save()
    else:
        with pytest.raises(IntegrityError):
            preset.save()


@pytest.mark.parametrize(
    "config, expected_valid", window_presets_tests, ids=ids
)
def test_window_presets_form(config, expected_valid):
    preset = WindowPreset(title="foo", **config)
    if expected_valid:
        preset.full_clean()
    else:
        with pytest.raises(ValidationError):
            preset.full_clean()
