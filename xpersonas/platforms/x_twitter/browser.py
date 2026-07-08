"""Browser session management for X/Twitter."""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import Browser, BrowserContext, async_playwright

_DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
)

_IGNORE_DEFAULT_ARGS = [
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-back-forward-cache",
    "--disable-component-extensions-with-background-pages",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=AvoidUnnecessaryBeforeUnloadCheckSync",
    "--disable-features=OptimizationHints",
    "--disable-hang-monitor",
    "--disable-ipc-flooding-protection",
    "--disable-renderer-backgrounding",
    "--disable-sync",
    "--export-tagged-pdf",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--no-service-autorun",
    "--password-store=basic",
    "--unsafely-disable-devtools-self-xss-warnings",
    "--use-mock-keychain",
]


class BrowserSession:
    """Manages a Playwright browser context for X/Twitter."""

    def __init__(
        self,
        headless: bool = True,
        auth_path: str | Path = "auth.json",
        executable_path: str | None = None,
        user_agent: str | None = None,
        viewport: dict | None = None,
        locale: str = "en-IN",
        slowmo: int = 0,
    ) -> None:
        self.headless = headless
        self.auth_path = Path(auth_path)
        self.executable_path = executable_path
        self.user_agent = user_agent or _DEFAULT_UA
        self.viewport = viewport or {"width": 1280, "height": 900}
        self.locale = locale
        self.slowmo = slowmo
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page = None

    async def start(self) -> BrowserContext:
        self._playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--force-device-scale-factor=1",
        ]

        context_kwargs: dict = dict(
            user_agent=self.user_agent,
            locale=self.locale,
            color_scheme="light",
            reduced_motion="no-preference",
            permissions=["clipboard-read", "clipboard-write"],
            is_mobile=False,
            has_touch=False,
        )
        if self.headless:
            context_kwargs["viewport"] = self.viewport
            context_kwargs["device_scale_factor"] = 1
        else:
            context_kwargs["no_viewport"] = True

        storage_state = str(self.auth_path) if self.auth_path.exists() else None

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
            executable_path=self.executable_path,
            ignore_default_args=_IGNORE_DEFAULT_ARGS,
            slowmo=self.slowmo,
        )
        self._context = await self._browser.new_context(
            storage_state=storage_state,
            **context_kwargs,
        )
        self.page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        return self._context

    async def save_auth_state(self) -> None:
        if self._context:
            try:
                await self._context.storage_state(path=str(self.auth_path))
            except Exception:
                pass

    async def stop(self) -> None:
        if self._context:
            await self.save_auth_state()
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self.page = None

    async def __aenter__(self) -> BrowserSession:
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.stop()
