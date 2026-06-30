from pathlib import Path
from pydantic import BaseModel, Field


class ProfileStats(BaseModel):
    handle: str
    display_name: str
    bio: str = Field(default="")
    location: str | None = Field(default=None)
    website: str | None = Field(default=None)
    followers: int = Field(default=0)
    following: int = Field(default=0)
    posts_count: int = Field(default=0)
    joined: str = Field(default="")
    verified: bool = Field(default=False)


class MediaAttachment(BaseModel):
    file_path: Path = Field(description="Absolute or project-relative path to the media file.")

    def resolve(self) -> Path:
        """Return the resolved absolute path, raising if the file is missing."""
        resolved = self.file_path.resolve()
        if not resolved.is_file():
            msg = f"Media file not found: {resolved}"
            raise FileNotFoundError(msg)
        return resolved
