"""Visual-theme regression checks for the viva backup pipeline."""

from pathlib import Path


SLIDES_PATH = Path("docs/viva/slides/index.html")


def test_backup_guide_line_uses_each_layer_theme_colour():
    """The guide beside each layer should not depend on content-height percentages."""
    source = SLIDES_PATH.read_text(encoding="utf-8")

    assert ".pipeline-layer::after" in source
    assert "background:var(--layer-color)" in source
    assert ".backup-pipeline::before" not in source
