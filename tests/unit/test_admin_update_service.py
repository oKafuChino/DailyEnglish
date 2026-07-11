import pytest

from app.services.admin_update_service import AdminUpdateService, truncate_output


class FakeProcess:
    returncode = 0

    async def communicate(self) -> tuple[bytes, None]:
        return b"updated\n", None

    def kill(self) -> None:
        return None


@pytest.mark.asyncio
async def test_admin_update_service_runs_configured_command() -> None:
    async def runner(command: str) -> FakeProcess:
        assert command == "deploy"
        return FakeProcess()

    result = await AdminUpdateService(
        command="deploy",
        timeout_seconds=30,
        runner=runner,
    ).run()

    assert result.succeeded
    assert result.output == "updated"


@pytest.mark.asyncio
async def test_admin_update_service_requires_configured_command() -> None:
    with pytest.raises(ValueError):
        await AdminUpdateService(command="", timeout_seconds=30).run()


@pytest.mark.asyncio
async def test_admin_update_service_reports_start_failure() -> None:
    async def runner(command: str) -> FakeProcess:
        raise FileNotFoundError(command)

    result = await AdminUpdateService(
        command="missing-command",
        timeout_seconds=30,
        runner=runner,
    ).run()

    assert not result.succeeded
    assert result.return_code == 127
    assert "failed to start update command" in result.output


def test_truncate_output_keeps_tail() -> None:
    assert truncate_output("abcdef", limit=3) == "def"
