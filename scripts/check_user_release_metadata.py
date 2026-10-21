"""Guard user-facing Web production releases against missed version/news metadata.

Only used by V3 production promotion and independent Hosting publication.
Staging is intentionally not gated, so multiple development commits can share
one candidate version. The SHA and changed paths come from actual Git objects,
not commit text, documentation claims, or an AI classifier.
"""
import argparse
import re
import subprocess
import sys

VERSION = re.compile(r"(?m)^version:\s*(\d+)\.(\d+)\.(\d+)\+(\d+)\s*$")
NOTE_START = re.compile(r"\bLifeReleaseNote\s*\(")
NOTE_ID = re.compile(r"\bid:\s*'([^']+)'")
NOTE_VERSION = re.compile(r"\bversion:\s*'([^']+)'")
NOTE_FEATURE = re.compile(r"\bfeatureKey:\s*'([^']+)'")
USER_SURFACES = {
    "lib/web/gmail_radar_page.dart": "gmail_radar",
    "lib/web/life_capture_page.dart": "life_inbox",
}
SHA = re.compile(r"^[a-f0-9]{40}$")


def parsed_version(text: str) -> tuple[int, int, int, int]:
    match = VERSION.search(text)
    if match is None:
        raise ValueError("pubspec.yaml needs a version: MAJOR.MINOR.PATCH+build")
    return tuple(int(value) for value in match.groups())


def notes_by_id(source: str) -> dict[str, tuple[str, str | None]]:
    sections = NOTE_START.split(source)
    out: dict[str, tuple[str, str | None]] = {}
    for segment in sections[1:]:
        identifier, version = NOTE_ID.search(segment), NOTE_VERSION.search(segment)
        if identifier is None or version is None:
            continue
        feature = NOTE_FEATURE.search(segment)
        if identifier.group(1) in out:
            raise ValueError("Duplicate product news ID: " + identifier.group(1))
        out[identifier.group(1)] = (version.group(1),
                                    feature.group(1) if feature else None)
    return out


def is_user_web_path(path: str) -> bool:
    if path in ("lib/web/release_info.dart",):
        return False
    return ((path.startswith("lib/") and path.endswith(".dart"))
            or path.startswith("web/") or path.startswith("assets/"))


def validate(
    old_version_text: str,
    next_version_text: str,
    old_notes_text: str,
    next_notes_text: str,
    changed_paths: list[str],
) -> list[str]:
    """Pure validation for release metadata; errors must block publishing."""
    web_sources = [p for p in changed_paths if is_user_web_path(p)]
    if not web_sources:
        return []
    errors: list[str] = []
    old_version = parsed_version(old_version_text)
    new_version = parsed_version(next_version_text)
    if new_version[:3] <= old_version[:3] or new_version[3] <= old_version[3]:
        errors.append("User-facing Web changes need a newer MAJOR.MINOR.PATCH and build number")
    current_label = ".".join(str(value) for value in new_version[:3])
    old_notes = notes_by_id(old_notes_text)
    new_notes = notes_by_id(next_notes_text)
    fresh = {
        name: values for name, values in new_notes.items()
        if name not in old_notes and values[0] == current_label
    }
    if not fresh:
        errors.append("User-facing Web changes need a new latest-news entry for " + current_label)
    required_features = {USER_SURFACES[path] for path in web_sources if path in USER_SURFACES}
    for key in sorted(required_features):
        if not any(feature == key for _, feature in fresh.values()):
            errors.append("Missing rollout-scoped latest-news entry: " + key)
    return errors


def _git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    args = parser.parse_args()
    if not SHA.fullmatch(args.base_sha) or not SHA.fullmatch(args.head_sha):
        parser.error("Exact 40-character source SHAs are mandatory")
    try:
        files = _git("diff", "--name-only", args.base_sha, args.head_sha).splitlines()
        errors = validate(
            _git("show", args.base_sha + ":pubspec.yaml"),
            _git("show", args.head_sha + ":pubspec.yaml"),
            _git("show", args.base_sha + ":lib/web/release_info.dart"),
            _git("show", args.head_sha + ":lib/web/release_info.dart"),
            files,
        )
    except (ValueError, subprocess.CalledProcessError) as exc:
        print("user_release_metadata=FAIL: " + str(exc), file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print("user_release_metadata=FAIL: " + error, file=sys.stderr)
        return 1
    print("user_release_metadata=PASS user_web_files=%d base=%s head=%s"
          % (sum(map(is_user_web_path, files)), args.base_sha, args.head_sha))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
