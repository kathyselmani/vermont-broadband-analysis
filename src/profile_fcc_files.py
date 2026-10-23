"""Backward-compatible wrapper. Prefer: `uv run vermont-broadband-analysis profile`."""

from vermont_broadband_analysis.fcc import profile

if __name__ == "__main__":
    profile()
