"""Visual-theme regression checks for the viva backup pipeline."""

from pathlib import Path


SLIDES_PATH = Path("docs/viva/slides/index.html")


def test_backup_guide_line_uses_each_layer_theme_colour():
    """The layer guide should not depend on content-height percentages."""
    source = SLIDES_PATH.read_text(encoding="utf-8")

    assert ".pipeline-layer::after" in source
    assert "background:var(--layer-color)" in source
    assert ".backup-pipeline::before" not in source


def test_teamwork_owns_end_to_end_navigation():
    """End-to-end belongs in Teamwork, not the layer-level navigation."""
    source = SLIDES_PATH.read_text(encoding="utf-8")
    top_nav = source.split('<nav class="backup-layer-nav"', 1)[1]
    top_nav = top_nav.split("</nav>", 1)[0]

    assert "End-to-end" not in top_nav
    assert "T7 · End-to-end integration" in source
    assert "scrollBackupTo('backupOverview')" in source


def test_teamwork_and_report_have_backup_topic_navigation():
    """Teamwork and Report should expose Model-style topic navigation."""
    source = SLIDES_PATH.read_text(encoding="utf-8")

    assert 'aria-label="Teamwork backup topics"' in source
    assert 'aria-label="Report backup topics"' in source
    assert "scrollBackupTo('teamworkBrief')" in source
    assert "openBackupNode('reportB0')" in source
    assert "openBackupNode('reportB11')" in source
