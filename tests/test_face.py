import numpy as np
import pytest

from app.face.similarity import cosine_similarity, is_match


def test_cosine_identical():
    a = np.array([1.0, 0.0, 0.0])
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_orthogonal():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_opposite():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert cosine_similarity(a, b) == pytest.approx(-1.0)


def test_is_match_above_threshold():
    assert is_match(0.87, threshold=0.65) is True


def test_is_match_below_threshold():
    assert is_match(0.40, threshold=0.65) is False


def test_is_match_at_threshold():
    assert is_match(0.65, threshold=0.65) is True


def test_cosine_zero_vector():
    a = np.zeros(512)
    b = np.random.randn(512)
    assert cosine_similarity(a, b) == pytest.approx(0.0)
