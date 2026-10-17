#!/usr/bin/env python3
"""
Unified Entrypoint: Burkhard-Keller Metric Space Image Deduplicator
Course: Data Structures & Algorithms (DSA)

Usage:
  python run.py             # Launches the Modern Interactive Web Dashboard (Recommended)
  python run.py --desktop   # Launches the Native CustomTkinter Desktop GUI
  python run.py --help      # Displays usage and algorithmic summary
"""

import sys
import os
import argparse

# Ensure local module directory is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.join(PROJECT_ROOT, "Antigravity ver")
if MODULE_DIR not in sys.path:
    sys.path.insert(0, MODULE_DIR)

BANNER = r"""
========================================================================
   🌲 BK-TREE METRIC SPACE IMAGE DEDUPLICATOR & LIVE DSA BENCHMARK
========================================================================
Course:     Data Structures & Algorithms (DSA)
Metric:     Discrete Hamming Metric on 100-Bit Perceptual Hashes
Pruning:    Strict Triangle Inequality Subtree Elimination: |d1 - d2| <= tau
========================================================================
"""

def launch_web(port=8080):
    print(BANNER)
    print(f"[*] Starting Modern Web Studio on http://localhost:{port} ...")
    print("    - Features interactive SVG tree visualization and live O(N) benchmark comparison.")
    print("    - One-click 'Load Demo Dataset' included for instant grading.")
    print("=" * 72)
    
    # Change working directory so relative assets and templates resolve accurately
    os.chdir(MODULE_DIR)
    
    import web_app
    # Set default port if specified
    web_app.PORT = port
    web_app.start_server(port=port)


def launch_desktop():
    print(BANNER)
    print("[*] Launching Native CustomTkinter Desktop GUI ...")
    os.chdir(MODULE_DIR)
    try:
        import customtkinter
    except ImportError:
        print("\n[!] Error: 'customtkinter' is required for Desktop GUI mode.")
        print("    Install it via: pip install customtkinter")
        print("    Or launch the Web Dashboard without extra GUI dependencies via: python run.py\n")
        sys.exit(1)

    import app
    desktop_app = app.DeduplicatorApp()
    desktop_app.mainloop()


def main():
    parser = argparse.ArgumentParser(
        description="BK-Tree Metric Space Image Deduplication Suite (DSA Project)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python run.py            # Launch interactive Web Studio (Recommended for viva & grading)
  python run.py --desktop  # Launch native CustomTkinter desktop interface
  python run.py --port 9000# Launch web studio on custom port
"""
    )
    parser.add_argument(
        "--desktop", "--gui",
        action="store_true",
        help="Launch the native CustomTkinter Desktop GUI instead of the Web Studio"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="HTTP port for the Web Studio (default: 8080)"
    )

    args = parser.parse_args()

    if args.desktop:
        launch_desktop()
    else:
        launch_web(port=args.port)


if __name__ == "__main__":
    main()
