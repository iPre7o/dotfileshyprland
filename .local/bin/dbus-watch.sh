#!/bin/sh
while sleep 30; do
  B=$(pgrep -u "$USER" -x dbus-broker | head -1)
  top=$(busctl --user list --no-pager --unique 2>/dev/null | awk 'NR>1{print $3}' | sort | uniq -c | sort -rn | head -4 | tr -s ' ' | tr '\n' ';')
  echo "$(date +%F_%T) broker_fds=$(ls /proc/$B/fd 2>/dev/null | wc -l) $top"
done >> "$HOME/.cache/dbus-watch.log" 2>&1
