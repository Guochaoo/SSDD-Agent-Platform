from app.core.redis_client import RedisClient
import main


def test_redis_cleanup_lock_only_releases_its_own_token(monkeypatch):
    calls = []

    class FakeRedis:
        def set(self, *args, **kwargs):
            calls.append(("set", args, kwargs))
            return True

        def eval(self, *args):
            calls.append(("eval", args, {}))
            return 1

    monkeypatch.setattr("app.core.redis_client.redis.from_url", lambda *_args, **_kwargs: FakeRedis())
    client = RedisClient()

    assert client.acquire_lock("cleanup", "token-1", 60) is True
    client.release_lock("cleanup", "token-1")
    assert calls[0] == ("set", ("cleanup", "token-1"), {"nx": True, "ex": 60})
    assert calls[1][0] == "eval"
    assert calls[1][1][1:] == (1, "cleanup", "token-1")


def test_cleanup_runner_skips_when_another_worker_owns_lock(monkeypatch):
    class Lock:
        def acquire_lock(self, *_args):
            return False

        def release_lock(self, *_args):
            raise AssertionError("a lock that was not acquired must not be released")

    monkeypatch.setattr(main, "redis_client", Lock())
    monkeypatch.setattr(main, "SessionLocal", lambda: (_ for _ in ()).throw(AssertionError("database must not be opened")))

    assert main.retry_resource_cleanups() == {"attempted": 0, "succeeded": 0, "skipped": True}


def test_cleanup_runner_releases_lock_after_retry(monkeypatch):
    events = []

    class Lock:
        def acquire_lock(self, *_args):
            events.append("acquire")
            return True

        def release_lock(self, *_args):
            events.append("release")

    class Database:
        def close(self):
            events.append("close")

    monkeypatch.setattr(main, "redis_client", Lock())
    monkeypatch.setattr(main, "SessionLocal", Database)
    monkeypatch.setattr(main, "retry_pending_cleanups", lambda _db: {"attempted": 1, "succeeded": 1})

    assert main.retry_resource_cleanups() == {"attempted": 1, "succeeded": 1}
    assert events == ["acquire", "close", "release"]
