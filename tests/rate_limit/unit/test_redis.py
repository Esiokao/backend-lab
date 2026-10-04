from unittest.mock import Mock

from app.core.redis import RATE_LIMIT_SCRIPT, check_rate_limit


def test_check_rate_limit_allows_request(monkeypatch):
    """check if the request is allowed to proceed when the rate limit is not exceeded"""
    # mock the redis
    # allwways return 1
    mock_eval = Mock(return_value=1)

    # replace the eval func with the mock_eval
    monkeypatch.setattr("app.core.redis.redis_client.eval", mock_eval)

    result = check_rate_limit(
        key="rate_limit:test:127.0.0.1",
        limit=5,
        window=60,
    )

    # allowed
    assert result is True

    mock_eval.assert_called_once_with(
        RATE_LIMIT_SCRIPT,
        1,
        "rate_limit:test:127.0.0.1",
        60,
    )


def test_check_rate_limit_equal_to_limit(monkeypatch):
    """Allow the request when the count equals the rate limit."""
    # mock the redis
    # allwways return the limit
    limit = 5
    mock_eval = Mock(return_value=limit)

    # replace the eval func with the mock_eval
    monkeypatch.setattr("app.core.redis.redis_client.eval", mock_eval)

    result = check_rate_limit(
        key="rate_limit:test:127.0.0.1",
        limit=limit,
        window=60,
    )

    # allowed
    assert result is True

    mock_eval.assert_called_once_with(
        RATE_LIMIT_SCRIPT,
        1,
        "rate_limit:test:127.0.0.1",
        60,
    )


def test_check_rate_limit_exceeds_limit(monkeypatch):
    """Reject the request when the count exceeds the rate limit."""
    # mock the redis
    # allwways return the limit
    limit = 5
    exceed_times = limit + 1
    mock_eval = Mock(return_value=exceed_times)

    # replace the eval func with the mock_eval
    monkeypatch.setattr("app.core.redis.redis_client.eval", mock_eval)

    result = check_rate_limit(
        key="rate_limit:test:127.0.0.1",
        limit=limit,
        window=60,
    )

    # allowed
    assert result is False

    mock_eval.assert_called_once_with(
        RATE_LIMIT_SCRIPT,
        1,
        "rate_limit:test:127.0.0.1",
        60,
    )
