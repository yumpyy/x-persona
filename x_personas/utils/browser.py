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
    def __init__(
        self,
        headless: bool = True,
        auth_state_path: str = "auth.json",
        executable_path: str | None = None,
        user_data_dir: str | None = None,
        user_agent: str | None = None,
        timezone_id: str | None = None,
        locale: str = "en-IN",
        geolocation: dict | None = None,
        viewport: dict | None = None,
    ) -> None:
        self.headless = headless
        self.auth_state_path = Path(auth_state_path)
        self.executable_path = executable_path
        self.user_data_dir = user_data_dir
        self.user_agent = user_agent or _DEFAULT_UA
        self.timezone_id = timezone_id
        self.locale = locale
        self.geolocation = geolocation
        self.viewport = viewport or {"width": 1280, "height": 900}
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> BrowserContext:
        self._playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--force-device-scale-factor=1",
        ]
        if not self.headless:
            launch_args.append("--start-maximized")

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

        if self.timezone_id:
            context_kwargs["timezone_id"] = self.timezone_id
        if self.geolocation:
            context_kwargs["geolocation"] = self.geolocation

        if self.user_data_dir:
            context_kwargs["user_data_dir"] = self.user_data_dir
            context_kwargs["headless"] = self.headless
            context_kwargs["args"] = launch_args
            if self.executable_path:
                context_kwargs["executable_path"] = self.executable_path
            self._context = await self._playwright.chromium.launch_persistent_context(
                ignore_default_args=_IGNORE_DEFAULT_ARGS,
                **context_kwargs,
            )
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=launch_args,
                executable_path=self.executable_path,
                ignore_default_args=_IGNORE_DEFAULT_ARGS,
            )

            storage_state = (
                str(self.auth_state_path)
                if self.auth_state_path.exists()
                else None
            )
            self._context = await self._browser.new_context(
                storage_state=storage_state,
                **context_kwargs,
            )

        return self._context

    async def get_context(self) -> BrowserContext:
        if self._context is None:
            return await self.start()
        return self._context

    async def save_auth_state(self) -> None:
        if self._context:
            try:
                await self._context.storage_state(path=str(self.auth_state_path))
            except Exception as e:
                from x_personas.agent.log import log
                log(f"Warning: Could not save auth state (context may have already closed): {e}")

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

    async def __aenter__(self) -> BrowserContext:
        return await self.start()

    async def __aexit__(self, *args) -> None:
        await self.stop()
