#! /usr/bin/env bash
if [[ $1 -le 11 ]]; then
    jq "if .properties.ele_ft % 200 == 0 then . else {} end";
elif [[ $1 -eq 12 ]]; then
    jq "if .properties.ele_ft % 80 == 0 then . else {} end";
else
    cat;
fi
