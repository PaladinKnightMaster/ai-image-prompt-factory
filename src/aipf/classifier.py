from __future__ import annotations
import re

ARTIFACT_WORDS = {
    "marble", "bronze", "statue", "bust", "relief", "stele", "frieze", "ceramic", "porcelain",
    "vase", "plate", "bowl", "jar", "tile", "artifact", "sculpture"
}
STYLE_WORDS = {"watercolor", "ink painting", "ukiyo-e", "woodblock", "gongbi", "mural", "paper-cut", "embroidery", "manuscript miniature"}
HISTORY_WORDS = {"han", "tang", "song", "ming", "qing", "heian", "edo", "classical greek", "hellenistic", "roman", "dunhuang", "wuxia", "xianxia"}
LAYOUT_WORDS = {"poster", "infographic", "calendar", "catalog", "lookbook", "layout", "storyboard", "grid", "collage"}


def classify(text: str, has_references: bool = False) -> str:
    t = text.casefold()
    if any(w in t for w in LAYOUT_WORDS):
        return "storyboard_or_grid" if ("storyboard" in t or "grid" in t) else "design_layout"
    if any(w in t for w in ARTIFACT_WORDS):
        return "artifact_transform" if has_references or any(v in t for v in ["turn", "transform", "make me", "make this"]) else "new_generation"
    if any(w in t for w in HISTORY_WORDS):
        return "historical_portrait"
    if any(w in t for w in STYLE_WORDS):
        return "reference_transform" if has_references else "art_style_transform"
    if has_references or re.search(r"\b(turn|transform|edit|change)\b", t):
        return "reference_transform"
    return "new_generation"
