"""Testes do Lock distribuido por video (ADR-001/003) - Redis real."""
from __future__ import annotations

from worker.infrastructure.redis.lock import acquire, release, renew

VIDEO_ID = "video-abc"


async def test_acquire_succeeds_when_not_locked(redis_client) -> None:
    """O primeiro dono a pedir o lock deve consegui-lo."""
    acquired = await acquire(redis_client, VIDEO_ID, "worker-a", ttl_seconds=60)
    assert acquired is True


async def test_acquire_fails_when_already_locked_by_another_owner(redis_client) -> None:
    """Um segundo dono nao deve conseguir adquirir o mesmo lock."""
    await acquire(redis_client, VIDEO_ID, "worker-a", ttl_seconds=60)

    acquired = await acquire(redis_client, VIDEO_ID, "worker-b", ttl_seconds=60)

    assert acquired is False


async def test_release_only_works_for_the_correct_owner(redis_client) -> None:
    """release() so deve funcionar se o valor ainda pertencer ao dono correto."""
    await acquire(redis_client, VIDEO_ID, "worker-a", ttl_seconds=60)

    released_by_wrong_owner = await release(redis_client, VIDEO_ID, "worker-b")
    released_by_right_owner = await release(redis_client, VIDEO_ID, "worker-a")

    assert released_by_wrong_owner is False
    assert released_by_right_owner is True


async def test_release_allows_reacquisition(redis_client) -> None:
    """Depois de liberado pelo dono correto, outro Worker deve conseguir adquirir."""
    await acquire(redis_client, VIDEO_ID, "worker-a", ttl_seconds=60)
    await release(redis_client, VIDEO_ID, "worker-a")

    acquired = await acquire(redis_client, VIDEO_ID, "worker-b", ttl_seconds=60)

    assert acquired is True


async def test_renew_only_works_for_the_correct_owner(redis_client) -> None:
    """renew() so deve estender o TTL se o valor ainda pertencer ao dono correto."""
    await acquire(redis_client, VIDEO_ID, "worker-a", ttl_seconds=60)

    renewed_by_wrong_owner = await renew(redis_client, VIDEO_ID, "worker-b", ttl_seconds=120)
    renewed_by_right_owner = await renew(redis_client, VIDEO_ID, "worker-a", ttl_seconds=120)

    assert renewed_by_wrong_owner is False
    assert renewed_by_right_owner is True
