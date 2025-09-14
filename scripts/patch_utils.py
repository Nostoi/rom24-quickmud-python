# scripts/patch_utils.py
import re, subprocess, tempfile, pathlib

DIFF_BLOCK = re.compile(r"```diff(.*?)```", re.DOTALL | re.IGNORECASE)

def extract_diffs(text: str) -> list[str]:
    return [m.group(1).strip() for m in DIFF_BLOCK.finditer(text)]

def apply_diff(diff_text: str, repo_root: str = ".") -> bool:
    # Use git apply with 3-way for resilience
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".patch") as f:
        f.write(diff_text)
        patch_path = f.name
    try:
        subprocess.run(
            ["git", "apply", "--3way", "--whitespace=nowarn", patch_path],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print("Patch failed:\n", e.stdout, e.stderr)
        return False
    finally:
        pathlib.Path(patch_path).unlink(missing_ok=True)
