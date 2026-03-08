"""Tests for greet function."""
import pytest
from myapp import greet


def test_greet_basic():
    assert greet("World") == "Hello, World!"


def test_greet_empty():
    assert greet("") == "Hello, !"


def test_greet_unicode():
    assert "Claude" in greet("Claude")
