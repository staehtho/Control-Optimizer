import time
from datetime import datetime


class Timer:
    def __init__(self):
        self.sections = {}
        self._current_label = None
        self._t0 = None

    def start(self, label: str):
        """Start a new timing section."""
        # Stop previous section if still running
        if self._current_label is not None:
            self.stop()

        self._current_label = label
        self._t0 = time.perf_counter()
        self.sections[label] = {
            "start": datetime.now().isoformat(timespec="milliseconds"),
            "duration": 0.0,
        }

    def stop(self):
        """Stop the current section."""
        if self._current_label is None:
            return

        dt = time.perf_counter() - self._t0
        self.sections[self._current_label]["duration"] += dt
        self._current_label = None
        self._t0 = None

    def stop_all(self):
        """Stop any running section."""
        if self._current_label is not None:
            self.stop()

    def report(self):
        """Print all timing sections."""
        print("\n=== Timing Report ===")
        for label, info in self.sections.items():
            print(f"{label:20s}  {info['duration']:.6f} s  (started {info['start']})")
        print("=====================\n")

    # Optional: context manager for "with" syntax
    def section(self, label: str):
        timer = self

        class _Section:
            def __enter__(self_inner):
                timer.start(label)

            def __exit__(self_inner, exc_type, exc, tb):
                timer.stop()

        return _Section()
