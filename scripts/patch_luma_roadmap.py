#!/usr/bin/env python3
"""
patch_luma_roadmap.py
─────────────────────
แก้ไข Luma CLI ให้ action_update_roadmap รองรับ comma-separated issue numbers
เช่น "33, 34" หรือ "33 34" แทนที่จะรับได้แค่ issue เดียว

Usage:
    python scripts/patch_luma_roadmap.py
    python scripts/patch_luma_roadmap.py --check   # dry-run: ตรวจสอบโดยไม่แก้ไข
"""

import argparse
import os
import sys

LUMA_ACTIONS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "Luma", "luma_core", "actions.py"
)

# ─── Marker ──────────────────────────────────────────────────────────────────
# ใส่ไว้เพื่อตรวจว่า patch ถูก apply แล้วหรือยัง
PATCH_MARKER = "# PATCHED: multi-issue support"

# ─── Old function signature (ใช้ระบุตำแหน่งที่จะแทนที่) ──────────────────────
OLD_FUNC_START = "\ndef action_update_roadmap(state: LumaState, project: dict):"
NEXT_FUNC_START = "\ndef action_archive_artifacts(state: LumaState, project: dict):"

# ─── New function ─────────────────────────────────────────────────────────────
NEW_FUNCTION = '''
def action_update_roadmap(state: LumaState, project: dict):  # PATCHED: multi-issue support
    """Update ROADMAP.md status for one or more issues (supports comma-separated input)."""
    print(f"\\n🗺️  Updating Roadmap for {project['name']}...")

    # Locate ROADMAP.md
    roadmap_paths = [
        os.path.join(project["path"], "docs", "ROADMAP.md"),
        os.path.join(project["path"], "ROADMAP.md"),
    ]
    roadmap_path = next((p for p in roadmap_paths if os.path.exists(p)), None)

    if not roadmap_path:
        print("❌ Roadmap not found in docs/ or root.")
        return

    try:
        with open(roadmap_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"❌ Failed to read roadmap: {e}")
        return

    # ── Input: รองรับ single ("65") หรือ comma/space-separated ("33, 34", "33 34") ──
    issue_input = input("Enter Issue # to update (e.g. 65 or 33, 34): ").strip()
    if not issue_input:
        return

    raw_ids = issue_input.replace(",", " ").split()
    issue_ids = [x.strip().replace("#", "") for x in raw_ids if x.strip().replace("#", "").isdigit()]

    if not issue_ids:
        print(f"❌ No valid issue numbers found in: {issue_input!r}")
        return

    import subprocess

    # ── Verify each issue via gh CLI ──────────────────────────────────────────
    for issue_id in issue_ids:
        print(f"🔍 Verifying Issue #{issue_id} via GitHub CLI...")
        try:
            gh_res = subprocess.run(
                [
                    "gh", "issue", "view", issue_id,
                    "--json", "title,state",
                    "-t", "{{.title}} ({{.state}})",
                ],
                cwd=project["path"],
                capture_output=True,
                text=True,
            )
            if gh_res.returncode == 0:
                print(f"   ✅ Found: {gh_res.stdout.strip()}")
            else:
                print(f"   ⚠️ Could not verify issue via gh: {gh_res.stderr.strip()}")
        except Exception as e:
            print(f"   ⚠️ GitHub CLI check failed: {e}")

    # ── Helper: find issue in roadmap and return metadata ────────────────────
    def _find_issue(issue_id, lines):
        found_idx = -1
        for i, line in enumerate(lines):
            if (
                f"**#{issue_id}" in line
                or f"#{issue_id} " in line
                or f"[#{issue_id}]" in line
            ):
                found_idx = i
                break

        if found_idx == -1:
            return found_idx, False, -1, "    - "

        is_table_row = lines[found_idx].strip().startswith("|")
        status_idx = -1
        indent = "    - "

        if is_table_row:
            status_idx = found_idx
            print(f"   Current row: {lines[found_idx].strip()}")
        else:
            for i in range(found_idx + 1, min(found_idx + 6, len(lines))):
                stripped = lines[i].strip()
                if (
                    stripped.startswith("- **Status:**")
                    or stripped.startswith("- ✅ **Done**")
                    or stripped.startswith("- 🟡 **In Progress**")
                    or "Status:" in stripped
                    or "✅ **Done**" in stripped
                ):
                    status_idx = i
                    print(f"   Current: {stripped}")
                    if lines[i].startswith("    -"):
                        indent = "    - "
                    elif lines[i].startswith("\\t-"):
                        indent = "\\t- "
                    break

        return found_idx, is_table_row, status_idx, indent

    # ── Find all requested issues ─────────────────────────────────────────────
    found_issues = []
    for issue_id in issue_ids:
        found_idx, is_table_row, status_idx, indent = _find_issue(issue_id, lines)
        if found_idx == -1:
            print(f"❌ Issue #{issue_id} not found in Roadmap.")
        else:
            print(f"✅ Found issue #{issue_id} at line {found_idx + 1}: {lines[found_idx].strip()}")
            found_issues.append((issue_id, found_idx, is_table_row, status_idx, indent))

    if not found_issues:
        print("❌ None of the specified issues were found in the Roadmap.")
        return

    # ── Ask for status ONCE — applies to all found issues ────────────────────
    issue_list = ", ".join(f"#{x[0]}" for x in found_issues)
    print(f"\\nSelecting status for {len(found_issues)} issue(s): {issue_list}")
    print("\\nSelect new status:")
    print("  [1] ✅ Done / Complete")
    print("  [2] 🟢 Ready")
    print("  [3] 🟡 In Progress / Todo")
    print("  [4] 🔴 Blocked")

    status_choice = input("Select [1-4]: ").strip()
    if status_choice not in ("1", "2", "3", "4"):
        print("❌ Invalid selection")
        return

    version = ""
    note = ""
    if status_choice == "1":
        version = input("Enter Version (e.g. v1.8.0, Enter to skip): ").strip()
        note = input("Enter Completion Note (Enter to skip): ").strip()

    # ── Apply updates in reverse line order to preserve indices ──────────────
    for issue_id, found_idx, is_table_row, status_idx, indent in sorted(
        found_issues, key=lambda x: x[1], reverse=True
    ):
        if status_choice == "1":
            status_prefix = "✅ Complete" if is_table_row else "✅ **Done**"
            if version and note:
                new_table_status = f"{status_prefix} ({version}) - {note}"
            elif version:
                new_table_status = f"{status_prefix} ({version})"
            elif note:
                new_table_status = f"{status_prefix} - {note}"
            else:
                new_table_status = f"{status_prefix}"
            new_status_line = (
                f"{indent}✅ **Done**"
                + (f" ({version})" if version else "")
                + (f" - {note}" if note else "")
            )
        elif status_choice == "2":
            new_table_status = "🟢 Ready"
            new_status_line = f"{indent}**Status:** 🟢 **Ready**"
        elif status_choice == "3":
            new_table_status = "🔲 Todo" if is_table_row else "🟡 In Progress"
            new_status_line = f"{indent}**Status:** 🟡 **In Progress**"
        else:  # "4"
            new_table_status = "🔴 Blocked"
            new_status_line = f"{indent}**Status:** 🔴 **Blocked**"

        if is_table_row:
            parts = lines[found_idx].split("|")
            status_col_index = -2 if lines[found_idx].rstrip().endswith("|") else -1
            if len(parts) >= 3:
                parts[status_col_index] = f" {new_table_status} "
                lines[found_idx] = "|".join(parts)
                if not lines[found_idx].endswith("\\n"):
                    lines[found_idx] += "\\n"
            else:
                print(f"⚠️  Issue #{issue_id}: row does not have standard table formatting.")
        elif status_idx != -1:
            lines[status_idx] = new_status_line + "\\n"
        else:
            print(f"⚠️  Issue #{issue_id}: status line not found nearby. Appending.")
            lines.insert(found_idx + 2, new_status_line + "\\n")

        print(f"   ✅ Issue #{issue_id} → updated.")

    # ── Write back once ───────────────────────────────────────────────────────
    try:
        with open(roadmap_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"\\n✅ Roadmap updated successfully! ({len(found_issues)} issue(s))")
    except Exception as e:
        print(f"❌ Failed to write roadmap: {e}")

'''


# ─── Patch logic ──────────────────────────────────────────────────────────────


def load_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def is_already_patched(content: str) -> bool:
    return PATCH_MARKER in content


def apply_patch(content: str) -> str:
    """Replace old action_update_roadmap with the new multi-issue version."""
    start_idx = content.find(OLD_FUNC_START)
    if start_idx == -1:
        raise ValueError(
            "Could not find 'action_update_roadmap' function in the target file.\n"
            "The Luma CLI may have been updated — patch needs to be reviewed."
        )

    end_idx = content.find(NEXT_FUNC_START, start_idx)
    if end_idx == -1:
        raise ValueError(
            "Could not find the function that follows 'action_update_roadmap'.\n"
            "Cannot safely determine where the function ends."
        )

    # Replace: keep everything before + new function + everything from next func onward
    patched = content[:start_idx] + NEW_FUNCTION + content[end_idx:]
    return patched


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: verify the patch can be applied without modifying anything.",
    )
    args = parser.parse_args()

    target = os.path.abspath(LUMA_ACTIONS_PATH)

    if not os.path.exists(target):
        print(f"❌ Target file not found: {target}")
        print(
            "   Make sure the Luma project is at ../Luma/ relative to the Akasa project."
        )
        sys.exit(1)

    print(f"🔧 Target: {target}")

    content = load_file(target)

    if is_already_patched(content):
        print("✅ Already patched — nothing to do.")
        return

    try:
        patched = apply_patch(content)
    except ValueError as e:
        print(f"❌ Patch failed: {e}")
        sys.exit(1)

    # Sanity check: new function marker must be present
    if PATCH_MARKER not in patched:
        print("❌ Patch marker not found after applying patch — aborting.")
        sys.exit(1)

    if args.check:
        print("✅ Dry-run successful — patch can be applied cleanly.")
        print("   Run without --check to apply.")
        return

    # Backup
    backup_path = target + ".bak"
    write_file(backup_path, content)
    print(f"💾 Backup saved: {backup_path}")

    # Write patched file
    write_file(target, patched)
    print("✅ Patch applied successfully!")
    print()
    print("What changed:")
    print("  • input prompt updated: 'Enter Issue # to update (e.g. 65 or 33, 34)'")
    print("  • comma-separated and space-separated issue numbers are now supported")
    print("  • each issue is verified via gh CLI individually")
    print("  • status is selected ONCE and applied to all specified issues")
    print("  • line updates applied in reverse order to preserve line indices")
    print("  • roadmap file written once at the end")


if __name__ == "__main__":
    main()
