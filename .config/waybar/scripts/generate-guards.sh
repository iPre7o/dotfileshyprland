#!/usr/bin/env bash
# Gera overrides em ~/.local/share/applications a partir de
# single-instance-apps.conf, envolvendo o Exec= de cada app com app-guard.sh.
#
# Idempotente: rode de novo sempre que editar a lista ou depois que um app
# atualizar seu .desktop original (ex: apos update do pacote).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$SCRIPT_DIR/single-instance-apps.conf"
GUARD="$SCRIPT_DIR/app-guard.sh"
DEST_DIR="$HOME/.local/share/applications"
SEARCH_DIRS=("$DEST_DIR" "/usr/local/share/applications" "/usr/share/applications")

mkdir -p "$DEST_DIR"

find_original() {
  local name="$1"
  for d in "${SEARCH_DIRS[@]:1}"; do
    if [[ -f "$d/$name" ]]; then
      echo "$d/$name"
      return 0
    fi
  done
  return 1
}

while IFS='|' read -r name regex wrapper; do
  name="$(echo "$name" | xargs)"
  regex="$(echo "$regex" | xargs)"
  wrapper="$(echo "${wrapper:-}" | xargs)"
  [[ -z "$name" || "$name" == \#* ]] && continue

  src="$(find_original "$name")" || {
    echo "aviso: $name nao encontrado em /usr/share/applications, pulando" >&2
    continue
  }

  prefix="$GUARD '$regex' --"
  if [[ -n "$wrapper" ]]; then
    prefix="$prefix $SCRIPT_DIR/$wrapper"
  fi

  dest="$DEST_DIR/$name"
  awk -v prefix="$prefix" '
    BEGIN { done = 0 }
    /^Exec=/ && !done {
      line = $0
      sub(/^Exec=/, "", line)
      print "Exec=" prefix " " line
      done = 1
      next
    }
    { print }
  ' "$src" > "$dest"

  echo "gerado: $dest (de $src)"
done < "$CONF"
