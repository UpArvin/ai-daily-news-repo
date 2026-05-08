#!/usr/bin/env python3
import contextlib
import importlib.util
import io
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "setup_guide.py"


def load_setup_guide():
    spec = importlib.util.spec_from_file_location("setup_guide", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_provider_menu_options_are_four_tuples():
    setup_guide = load_setup_guide()
    with contextlib.redirect_stdout(io.StringIO()):
        options = setup_guide._print_provider_menu()

    assert options
    for option in options:
        assert len(option) == 4
        num, name, desc, fields = option
        assert isinstance(num, str)
        assert isinstance(name, str)
        assert isinstance(desc, str)
        assert isinstance(fields, list)


def test_skip_option_has_empty_fields():
    setup_guide = load_setup_guide()
    with contextlib.redirect_stdout(io.StringIO()):
        options = setup_guide._print_provider_menu()

    skip = next(option for option in options if option[0] == "0")
    assert skip[3] == []


if __name__ == "__main__":
    test_provider_menu_options_are_four_tuples()
    test_skip_option_has_empty_fields()
    print("✓ llm-tasks setup_guide tests passed")
