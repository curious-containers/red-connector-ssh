#!/bin/bash

RESULT_FILES_DIR="result-files"
ACCESS_FILES_DIR="access-files"

if [ "$(basename "$PWD")" = "red-connector-ssh" ]; then
  cd tests || exit 1
fi

if [ -d "$RESULT_FILES_DIR" ]; then
  rm -r "$RESULT_FILES_DIR"
fi

mkdir -p "$RESULT_FILES_DIR"

# test receive-file
echo "Running receive-file"
jq -M -s '.[0] * .[1]' "$ACCESS_FILES_DIR/auth.json" "$ACCESS_FILES_DIR/receive-file.json" > "access.json"
red-connector-ssh receive-file access.json "$RESULT_FILES_DIR/testfile.txt"

if [ ! -f "$RESULT_FILES_DIR/testfile.txt" ]; then
  echo "  ERROR: failed to create result file with \"receive-file\""
  exit 1
fi
echo "  Done"

# test receive-directory
echo "Running receive-dir"
jq -M -s '.[0] * .[1]' "$ACCESS_FILES_DIR/auth.json" "$ACCESS_FILES_DIR/receive-dir.json" > "access.json"
red-connector-ssh receive-dir access.json "$RESULT_FILES_DIR/testdir"

if [ ! -d "$RESULT_FILES_DIR/testdir" ]; then
  echo "  ERROR: failed to create result directory with \"receive-dir\""
  exit 1
fi
echo "  Done"

# test mount-directory
echo "Running mount-dir"
jq -M -s '.[0] * .[1]' "$ACCESS_FILES_DIR/auth.json" "$ACCESS_FILES_DIR/mount-dir.json" > "access.json"
red-connector-ssh mount-dir access.json "$RESULT_FILES_DIR/testdir_mount"

if [ ! -d "$RESULT_FILES_DIR/testdir_mount" ]; then
  echo "  ERROR: failed to create result directory with \"mount-dir\""
  exit 1
fi
echo "  Done"

echo "Running umount-dir"
red-connector-ssh umount-dir "$RESULT_FILES_DIR/testdir_mount"
echo "  Done"

# test send-file
echo "Running send-file"
jq -M -s '.[0] * .[1]' "$ACCESS_FILES_DIR/auth.json" "$ACCESS_FILES_DIR/send-file.json" > "access.json"
red-connector-ssh send-file access.json "$RESULT_FILES_DIR/testfile.txt"
echo "  Done"

# test send-dir
echo "Running send-dir"
jq -M -s '.[0] * .[1]' "$ACCESS_FILES_DIR/auth.json" "$ACCESS_FILES_DIR/send-dir.json" > "access.json"
red-connector-ssh send-dir access.json "$RESULT_FILES_DIR/testdir"
echo "  Done"
