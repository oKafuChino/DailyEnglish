import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateResult:
    return_code: int
    output: str
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0 and not self.timed_out


class AdminUpdateService:
    def __init__(
        self,
        *,
        command: str,
        timeout_seconds: int,
        runner: Callable[[str], Awaitable[asyncio.subprocess.Process]] | None = None,
    ) -> None:
        self.command = command.strip()
        self.timeout_seconds = timeout_seconds
        self.runner = runner or _create_shell_process

    async def run(self) -> UpdateResult:
        if not self.command:
            raise ValueError("Admin update command is not configured")

        try:
            process = await self.runner(self.command)
        except OSError as exc:
            return UpdateResult(
                return_code=127,
                output=f"failed to start update command: {type(exc).__name__}: {exc}",
            )
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_seconds,
            )
        except TimeoutError:
            process.kill()
            stdout, _ = await process.communicate()
            return UpdateResult(
                return_code=process.returncode or 124,
                output=_decode_output(stdout),
                timed_out=True,
            )
        return UpdateResult(
            return_code=process.returncode or 0,
            output=_decode_output(stdout),
        )


def _decode_output(value: bytes | None) -> str:
    if not value:
        return ""
    return value.decode("utf-8", errors="replace").strip()


async def _create_shell_process(command: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )


def truncate_output(value: str, *, limit: int = 3000) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]
