#!/usr/bin/env bash

gcd() {
  local a="$1"
  local b="$2"

  if (( a == b )); then
    echo "$a"
  elif (( a > b )); then
    gcd $((a - b)) "$b"
  else
    gcd "$a" $((b - a))
  fi
}

while read -r a b; do
  [[ -z "$a" || -z "$b" ]] && break
  gcd "$a" "$b"
done
