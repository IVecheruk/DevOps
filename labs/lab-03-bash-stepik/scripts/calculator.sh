#!/usr/bin/env bash

while true; do
  read -r -p "First operand (or exit): " first
  [[ "$first" == "exit" ]] && echo "bye" && break

  read -r -p "Operation: " op
  read -r -p "Second operand: " second

  if [[ -z "$second" ]]; then
    echo "error"
    continue
  fi

  case "$op" in
    +) echo $((first + second)) ;;
    -) echo $((first - second)) ;;
    \*) echo $((first * second)) ;;
    /) echo $((first / second)) ;;
    %) echo $((first % second)) ;;
    \*\*) echo $((first ** second)) ;;
    *) echo "error" ;;
  esac
done
