# Wait for Minifig services, showing elapsed time while they settle.
wait-minifig() (
  setopt pipefail
  cd "$HOME/figma/figma" || return

  ./minifig system info | jq -r '"Active Minifig profile: \(.active_profile)"' || return

  local SECONDS=0 counts ready total
  while true; do
    counts=$(./minifig service ls --json | jq -r '
      map(select(.desired_active or .status != "stopped"))
      | [(map(select(.status == "healthy" or .status == "completed" or .status == "stopped")) | length), length]
      | @tsv
    ') || {
      printf '\n'
      return 1
    }
    read -r ready total <<< "$counts"
    printf '\rWaiting for Minifig... %dm %02ds (%d/%d) Ready\033[K' "$(( SECONDS / 60 ))" "$(( SECONDS % 60 ))" "$ready" "$total"
    (( ready == total )) && break
    sleep 5 || return
  done

  printf '\rMinifig ready after %dm %02ds.\033[K\n' "$(( SECONDS / 60 ))" "$(( SECONDS % 60 ))"
)
