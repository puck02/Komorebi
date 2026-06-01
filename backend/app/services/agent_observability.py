import json
import logging
from typing import Any

from app.schemas.journal import JournalLayout
from app.services.assets import AssetItem

LOGGER = logging.getLogger("komorebi.agent")
MAX_TEXT_LENGTH = 500


def log_agent_event(event: str, **fields: Any) -> None:
    payload = {"event": event, **{key: normalize_value(value) for key, value in fields.items()}}
    LOGGER.info(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True))


def layout_observability_summary(layout: JournalLayout, assets: list[AssetItem]) -> dict[str, Any]:
    asset_by_id = {asset.id: asset for asset in assets}
    decorations = layout.layout.decorations
    external_count = 0
    asset_ids = []
    for decoration in decorations:
        asset_ids.append(decoration.asset_id)
        asset = asset_by_id.get(decoration.asset_id)
        if asset is not None and asset.source != "internal":
            external_count += 1
    return {
        "canvas_height": layout.canvas.height,
        "image_count": len(layout.layout.images),
        "text_count": len(layout.layout.texts),
        "decorations": {
            "total": len(decorations),
            "unique_assets": len(set(asset_ids)),
            "external": external_count,
        },
        "asset_ids": asset_ids[:30],
    }


def issue_summary(issues: list[dict[str, Any]]) -> dict[str, Any]:
    issue_types = sorted({str(issue.get("type", "unknown")) for issue in issues})
    severities = sorted({str(issue.get("severity", "unknown")) for issue in issues if issue.get("severity")})
    return {"count": len(issues), "types": issue_types, "severities": severities}


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return value if len(value) <= MAX_TEXT_LENGTH else value[:MAX_TEXT_LENGTH] + "..."
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): normalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_value(item) for item in value]
    return str(value)
