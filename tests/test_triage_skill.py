"""The packaged usage-skill contract proof (DOCS-05, D-04).

The skill is the agent-facing half of the MCP install: it teaches a harness the
safe call sequence and the fail-closed rules. These tests keep it honest against
the shipped server and the ONE schema module, so the skill cannot drift into a
ghost tool, an undeclared case field, or an approval token the gate would reject:

* the declared tool surface equals the registered owned tools;
* every ``CaseInput`` and ``ApprovalToken`` field is named in the reference;
* every documented approval-token example validates with the real validator;
* the trigger-rich frontmatter and the fail-closed vocabulary are present;
* the skill names ``data/sats_tews.yaml`` as the authority instead of restating
  the TEWS bands.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from mcp import Client

from triagedesk.cli import main as cli_main
from triagedesk.core.schema import ApprovalToken, CaseInput
from triagedesk.mcp import server as server_module
from triagedesk.skills import SKILL_NAME, install_skill, skill_root

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_FILE = skill_root().joinpath("SKILL.md")
REFERENCE_FILE = skill_root().joinpath("references", "tool-contracts.md")

_JSON_FENCE_RE = re.compile(r"```json\n(.*?)```", re.DOTALL)


def _text() -> str:
    """Read the skill's ``SKILL.md``."""
    return SKILL_FILE.read_text(encoding="utf-8")


def _frontmatter() -> dict[str, Any]:
    """Parse the skill's YAML frontmatter (the harness's discovery contract)."""
    text = _text()
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    _, rest = text.split("---\n", 1)
    raw, _ = rest.split("\n---\n", 1)
    loaded = yaml.safe_load(raw)
    assert isinstance(loaded, dict), "SKILL.md frontmatter must be a mapping"
    return loaded


async def _registered_tools() -> set[str]:
    """The owned server's registered tool names, read in-memory (no subprocess)."""
    async with Client(server_module.server) as client:
        listed = await client.list_tools()
    return {tool.name for tool in listed.tools}


async def test_the_skill_declares_exactly_the_registered_tools() -> None:
    """The skill's declared surface is the server's surface — no ghost, no gap."""
    declared = set(_frontmatter()["metadata"]["tools"])
    registered = await _registered_tools()
    assert declared == registered, (
        f"the skill declares {sorted(declared)} but the server registers {sorted(registered)}"
    )


async def test_every_declared_tool_is_documented() -> None:
    """Each declared tool has its own section in the reference and a row in the skill."""
    skill = _text()
    reference = REFERENCE_FILE.read_text(encoding="utf-8")
    for name in await _registered_tools():
        assert f"`{name}`" in skill, f"SKILL.md does not name {name}"
        assert f"## `{name}`" in reference, f"tool-contracts.md has no {name} section"


def test_the_frontmatter_is_trigger_rich() -> None:
    """The description carries the phrases a harness needs to discover the skill."""
    frontmatter = _frontmatter()
    assert str(frontmatter["name"]).strip()
    description = str(frontmatter["description"]).lower()
    for trigger in ("triage", "sats", "tews", "commit", "clinician"):
        assert trigger in description, f"the skill description omits {trigger!r}"
    assert frontmatter["metadata"]["mcp-server"] == "triagedesk"


def test_the_reference_names_every_case_field() -> None:
    """Every ``CaseInput`` field the agent must supply is documented."""
    reference = REFERENCE_FILE.read_text(encoding="utf-8")
    missing = {name for name in CaseInput.model_fields if f"`{name}`" not in reference}
    assert not missing, f"tool-contracts.md omits CaseInput fields {sorted(missing)}"


def test_the_reference_names_every_approval_field() -> None:
    """Every ``ApprovalToken`` field is documented."""
    reference = REFERENCE_FILE.read_text(encoding="utf-8")
    missing = {name for name in ApprovalToken.model_fields if f"`{name}`" not in reference}
    assert not missing, f"tool-contracts.md omits ApprovalToken fields {sorted(missing)}"


def test_documented_tokens_pass_the_real_validator() -> None:
    """Every documented token is a token the gate would accept or a dismissal."""
    reference = REFERENCE_FILE.read_text(encoding="utf-8")
    decisions: set[str] = set()
    for block in _JSON_FENCE_RE.findall(reference):
        try:
            document = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(document, dict) or "decision" not in document:
            continue
        token = ApprovalToken.model_validate(document)
        decisions.add(token.decision)
        if token.decision != "dismiss":
            assert token.approved_by.strip() and token.role.strip()
            assert token.final_colour.strip()
    assert {"approve", "dismiss"} <= decisions, (
        f"the reference documents decisions {sorted(decisions)}; show an approve and a dismiss"
    )


def test_the_skill_keeps_the_fail_closed_vocabulary() -> None:
    """The signals that must stop a case before the queue are named in the skill."""
    skill = _text()
    for signal in (
        "missing_vitals",
        "no_match",
        "deferral",
        "out_of_scope",
        "abstained",
        "refused",
        "flag",
    ):
        assert signal in skill, f"SKILL.md does not name {signal!r}"


def test_the_skill_points_at_the_data_authority_not_a_second_band_table() -> None:
    """SATS bands stay in ``data/*.yaml``; the skill links to them."""
    skill = _text()
    assert "data/sats_tews.yaml" in skill
    assert "data/sats_discriminators.yaml" in skill
    # A restated TEWS band table would put a numeric threshold in the skill.
    assert not re.search(r"\|\s*\*?\*?TEWS total", skill, re.IGNORECASE)


def test_the_repo_harness_points_at_the_packaged_skill_source() -> None:
    """The checkout's own OpenCode config discovers the package skill without a copy."""
    config = json.loads((REPO_ROOT / "opencode.json").read_text(encoding="utf-8"))
    assert "./src/triagedesk/skills" in config["skills"]


def test_the_package_can_install_the_skill(tmp_path: Path) -> None:
    """The package's own copy function installs the skill, idempotently."""
    assert install_skill(tmp_path).startswith("wrote ")
    installed = tmp_path / SKILL_NAME
    assert (installed / "SKILL.md").is_file()
    assert (installed / "references" / "tool-contracts.md").is_file()
    assert install_skill(tmp_path).startswith("already installed: ")


def test_the_cli_exposes_the_skill_path_and_install(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A wheel-only install can locate and install the skill through ``triagedesk``."""
    assert cli_main(["skill", "path"]) == 0
    assert SKILL_NAME in capsys.readouterr().out

    assert cli_main(["skill", "install", "--path", str(tmp_path)]) == 0
    assert (tmp_path / SKILL_NAME / "SKILL.md").is_file()
