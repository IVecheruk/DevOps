#!/usr/bin/env bash

count="${1:-0}"

if ! [[ "$count" =~ ^-?[0-9]+$ ]]; then
  echo "No students"
elif (( count == 1 )); then
  echo "1 student"
elif (( count >= 2 && count <= 4 )); then
  echo "students"
elif (( count >= 5 )); then
  echo "A lot of students"
else
  echo "No students"
fi
