from exoarmur.stability.classifier import classify_failure_text


def test_classify_failure_text_prioritizes_async_signals():
    assert classify_failure_text("RuntimeError: coroutine was never awaited") == "ASYNC"


def test_classify_failure_text_detects_environment_errors():
    assert classify_failure_text("ModuleNotFoundError: No module named 'cryptography'") == "ENVIRONMENT"


def test_classify_failure_text_detects_determinism_failures():
    assert classify_failure_text("Snapshot mismatch: hash mismatch detected") == "DETERMINISM"


def test_classify_failure_text_falls_back_to_test_design():
    assert classify_failure_text("assert 1 == 2") == "TEST_DESIGN"
