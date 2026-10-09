"""TriageDesk — agentic triage-support tool.

Turns the vitals and presenting complaint a triage nurse already has into a
sourced, SATS-grounded priority level — and never moves a patient without a
named clinician's approval.

Layout (D-12):
    core/  — pure: schema, rules loader, citations (no llm/mcp/store imports)
    llm/   — local-model extraction edge (untrusted output, behind a wrapper)
    mcp/   — owned MCP server + the one adapter wiring seam
"""

__version__ = "0.1.0"
