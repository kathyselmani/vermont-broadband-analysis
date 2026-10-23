"""Backward-compatible wrapper. Prefer: `uv run vermont-broadband-analysis build`."""

from vermont_broadband_analysis.fcc import build

if __name__ == "__main__":
    build()
