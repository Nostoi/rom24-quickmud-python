import sys

from mud.scripts import convert_are_to_json as mod


def test_convert_are_cli_writes_output(tmp_path):
    out_dir = tmp_path / "areas"
    argv = [
        "convert_are_to_json",
        "area/chapel.are",
        "--out-dir",
        str(out_dir),
    ]
    old_argv = sys.argv
    try:
        sys.argv = argv
        mod.main()
    finally:
        sys.argv = old_argv

    out_file = out_dir / "chapel.json"
    assert out_file.exists()
    data = out_file.read_text()
    assert '"rooms"' in data
