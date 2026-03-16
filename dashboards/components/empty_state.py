"""Standard components for empty data states and info banners."""

from __future__ import annotations

import streamlit as st


def render_empty_state(
    message: str,
    cli_command: str | None = None,
    *,
    icon: str = "\u2139\ufe0f",
) -> None:
    """Render a consistent empty-state UI with optional CLI hint.

    Parameters
    ----------
    message:
        The user-facing explanation (supports **markdown**).
    cli_command:
        If provided, rendered as a copy-pasteable code block.
    icon:
        Emoji shown before the info banner.
    """
    st.info(f"{icon} {message}")
    if cli_command:
        st.markdown("**Next step** — run this in your terminal:")
        st.code(cli_command, language="bash")


def render_no_agent_data(agent_name: str) -> None:
    """Specific empty state for agents with no runs yet."""
    render_empty_state(
        f"No run data found for agent: **{agent_name}**",
        f"python -m super_agents run --agent {agent_name} --verbose",
    )


def render_crucix_not_installed() -> None:
    """Specific empty state when Crucix is missing."""
    render_empty_state(
        "Crucix is not installed. Run the setup command to enable live intelligence.",
        "python -m super_agents crucix setup",
        icon="\U0001f4e1",
    )
