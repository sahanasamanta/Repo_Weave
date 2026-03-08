import os

class DataFileAnalyzer:
    def analyze_files(self, file_paths):
        """Return list of data file descriptors (just path for now)."""
        return [{"path": fp} for fp in file_paths]