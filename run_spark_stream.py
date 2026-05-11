#!/usr/bin/env python3
"""Convenience runner for the Week 2 Spark stream processor."""

import sys

from spark_layer.stream_processor import main


if __name__ == "__main__":
    print("=" * 60)
    print("Starting PSX Spark Stream Processor")
    print("=" * 60)

    try:
        main()
    except KeyboardInterrupt:
        print("\nStream processor stopped by user.")
        sys.exit(0)
    except Exception as exc:
        print(f"\nError: {exc}")
        sys.exit(1)
