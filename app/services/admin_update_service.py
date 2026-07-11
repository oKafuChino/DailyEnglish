import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path


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
        runner: Callable[[list[str]], Awaitable[asyncio.subprocess.Process]] | None = None,
    ) -> None:
        self.command = command.strip()
        self.timeout_seconds = timeout_seconds
        self.runner = runner or _create_process

    async def run(self) -> UpdateResult:
        if not self.command:
            raise ValueError("Admin update command is not configured")
        argv = self._build_argv()

        try:
            process = await self.runner(argv)
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

    def _build_argv(self) -> list[str]:
        script = Path(self.command).expanduser()
        is_posix_absolute = self.command.startswith("/")
        if not script.is_absolute() and not is_posix_absolute:
            raise ValueError("Admin update command must be an absolute script path")
        if script.suffix not in {".sh", ".bash"}:
            raise ValueError("Admin update command must point to a .sh or .bash script")
        return ["bash", self.command if is_posix_absolute else str(script)]


def _decode_output(value: bytes | None) -> str:
    if not value:
        return ""
    return value.decode("utf-8", errors="replace").strip()


async def _create_process(argv: list[str]) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )


def truncate_output(value: str, *, limit: int = 3000) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]
