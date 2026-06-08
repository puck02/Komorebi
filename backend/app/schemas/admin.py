from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminPermissionsRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    can_manage_ai_settings: bool = Field(alias="canManageAiSettings")


class AiSettingsRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base_url: str = Field(alias="baseUrl")
    has_api_key: bool = Field(alias="hasApiKey")
    model: str
    review_model: str = Field(alias="reviewModel")


class AiSettingsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base_url: str | None = Field(default=None, alias="baseUrl", max_length=1024)
    api_key: str | None = Field(default=None, alias="apiKey", max_length=4096)
    model: str | None = Field(default=None, min_length=1, max_length=120)
    review_model: str | None = Field(default=None, alias="reviewModel", min_length=1, max_length=120)

    @field_validator("base_url", "api_key", "model", "review_model")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value
