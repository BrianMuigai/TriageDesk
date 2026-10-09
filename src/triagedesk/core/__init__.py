"""Pure core (D-13): schema, rules loader, citations.

This package must not import `llm`, `mcp`, or `store`. The purity boundary is a
published contract enforced by an AST guard test (QUAL-02).
"""
