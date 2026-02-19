"""Tests for git utility functions."""

import pytest
from codereview.git_utils import parse_diff


class TestParseDiff:
    def test_simple_diff(self):
        diff = """diff --git a/test.py b/test.py
index abc123..def456 100644
--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 import os
+import sys
 
 def main():
-    pass
+    print("hello")"""

        hunks = parse_diff(diff)
        assert len(hunks) == 1
        assert hunks[0].file == "test.py"
        assert "import sys" in hunks[0].added_lines
        assert "    pass" in hunks[0].removed_lines

    def test_multiple_files(self):
        diff = """diff --git a/a.py b/a.py
@@ -1 +1 @@
-old
+new
diff --git a/b.py b/b.py
@@ -1 +1 @@
-old2
+new2"""

        hunks = parse_diff(diff)
        assert len(hunks) == 2
        assert hunks[0].file == "a.py"
        assert hunks[1].file == "b.py"

    def test_empty_diff(self):
        hunks = parse_diff("")
        assert len(hunks) == 0
