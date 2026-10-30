import pytest

from formflow.sample_factory import SampleKind, render_sample


def test_sample_factory_is_deterministic_for_the_same_seed() -> None:
    first = render_sample(SampleKind.NOISY, seed=20261030)
    second = render_sample(SampleKind.NOISY, seed=20261030)

    assert first.image.tobytes() == second.image.tobytes()
    assert first.ground_truth == second.ground_truth
    assert first.ambiguous_keys == second.ambiguous_keys


@pytest.mark.parametrize("kind", list(SampleKind))
def test_every_sample_represents_all_sixteen_fields(kind: SampleKind) -> None:
    sample = render_sample(kind, seed=42)

    assert len(sample.ground_truth) == 16


def test_clean_sample_has_complete_product_pairs() -> None:
    sample = render_sample(SampleKind.CLEAN, seed=42)

    assert all(value is not None for value in sample.ground_truth.values())
    assert sample.ambiguous_keys == ()


def test_review_sample_marks_at_least_one_nonblank_field_as_ambiguous() -> None:
    sample = render_sample(SampleKind.REVIEW, seed=42)

    assert sample.ambiguous_keys
    assert all(sample.ground_truth[key] is not None for key in sample.ambiguous_keys)
