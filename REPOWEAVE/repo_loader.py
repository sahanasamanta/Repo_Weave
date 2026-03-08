import os
from git import Repo

class RepoLoader:
    def __init__(self, repo_url=None, local_path=None, workspace="workspace"):
        self.repo_url = repo_url
        self.local_path = local_path
        self.workspace = workspace
        os.makedirs(workspace, exist_ok=True)

    def clone_repo(self):
        if self.local_path and os.path.exists(self.local_path):
            return self.local_path
        if not self.repo_url:
            raise ValueError("No repository source provided.")
        repo_name = self.repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        repo_path = os.path.join(self.workspace, repo_name)
        if not os.path.exists(repo_path):
            print(f"Cloning {self.repo_url} ...")
            Repo.clone_from(self.repo_url, repo_path)
        else:
            print("Repository already cloned.")
        return repo_path

    def scan_files(self, repo_path):
        python_files = []
        data_files = []  # all non-Python files that could be data
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, repo_path)
                if file.endswith('.py'):
                    python_files.append(rel_path)
                else:
                    # Consider everything else a data file (extend as needed)
                    data_files.append(rel_path)
        return {
            "python_files": python_files,
            "data_files": data_files
        }

    def load_repository(self):
        repo_path = self.clone_repo()
        file_map = self.scan_files(repo_path)
        print("\nRepository Scan Complete")
        print("------------------------")
        for key, files in file_map.items():
            print(f"{key}: {len(files)} files")
        return repo_path, file_map