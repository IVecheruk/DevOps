#!/usr/bin/env bash

while true; do
  read -r -p "Enter your name: " name
  read -r -p "Enter your age: " age

  if [[ -z "$name" || "$age" == "0" ]]; then
    echo "bye"
    break
  fi

  if (( age < 18 )); then
    echo "child"
  elif (( age < 30 )); then
    echo "youth"
  else
    echo "adult"
  fi
done
