#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
#  P2P Merchant Price Bot — Uninstaller
#
#  Asks what to remove:
#    1) Erase EVERYTHING install.sh created
#         systemd service · bot process · cron @reboot entry ·
#         the whole install directory (source, venv, config.json, data.json)
#    2) Keep my data
#         same as 1), but config.json + data.json (+ .env) are saved
#         to a backup folder first
#
#  Usage:
#    bash uninstall.sh                  # interactive: asks 1) / 2) / cancel
#    bash uninstall.sh --full           # erase everything (no ask)
#    bash uninstall.sh --keep-data      # erase everything but the json data
#    bash uninstall.sh --dir /opt/p2p-bot --full --yes
#
#  Without a terminal (and without a flag) it defaults to KEEPING the data —
#  nothing is erased unless you answer "1" or pass --full.
#
#  NOTE: apt packages install.sh may have installed (python3, pip, venv, git,
#  curl, wget, ca-certificates) are NOT removed — other software on the
#  machine may depend on them.
# ─────────────────────────────────────────────────────────────

SERVICE_NAME="p2p-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# ── colours ──
if [[ -t 1 ]]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; CYAN=''; BOLD=''; DIM=''; NC=''
fi
info()  { echo -e "${CYAN}ℹ️  $*${NC}"; }
ok()    { echo -e "${GREEN}✅ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
err()   { echo -e "${RED}❌ $*${NC}" >&2; }
step()  { echo -e "\n${BOLD}━━ $* ━━${NC}"; }

SUDO=""; [[ $EUID -ne 0 ]] && SUDO="sudo"

INSTALL_DIR=""
MODE=""          # "full" | "keep"
ASSUME_YES=0

usage() {
  cat <<EOF
${BOLD}P2P Bot — Uninstaller${NC}
Usage: bash uninstall.sh [OPTIONS]

Options:
  --full               Erase EVERYTHING install.sh created: service, bot
                       process, cron entry, the whole install directory
                       (source, venv, config.json, data.json)
  --keep-data          Erase everything BUT save config.json + data.json
                       (+ .env) into a backup folder first.
                       This is the default when there is no terminal.
  --dir PATH           Install directory (default: auto-detected from the
                       systemd service, the current directory, or the usual
                       install locations)
  --yes, -y            Do not ask for confirmation
  --help, -h           Show this help

apt packages (python3, pip, git, curl, wget, …) are never removed — other
software on the machine may depend on them.

Examples:
  bash uninstall.sh                     # asks what to remove
  bash uninstall.sh --full --yes        # wipe everything, no questions
  bash uninstall.sh --keep-data         # uninstall, save the json data
  bash uninstall.sh --dir /opt/p2p-bot --full
EOF
}

# ── never run from a directory we might delete ────────────────────────────
# The full erase removes the install directory.  If this script itself lives
# inside it, copy it to a temp file and re-exec, so bash never loses the file
# it is reading when the directory is wiped.
if [[ -z "${P2P_UNINSTALL_COPIED:-}" && -n "${BASH_SOURCE[0]:-}" && -f "${BASH_SOURCE[0]}" ]] \
   && grep -q "P2P Merchant Price Bot — Uninstaller" "${BASH_SOURCE[0]}" 2>/dev/null; then
  _self_tmp="$(mktemp "${TMPDIR:-/tmp}/p2p-uninstall.XXXXXX.sh")" 2>/dev/null || _self_tmp=""
  if [[ -n "$_self_tmp" ]] && cp -f "${BASH_SOURCE[0]}" "$_self_tmp" 2>/dev/null; then
    chmod +x "$_self_tmp" 2>/dev/null || true
    P2P_UNINSTALL_COPIED=1 exec bash "$_self_tmp" "$@"
  fi
fi

# ── remove our own temporary copy on every exit path ──
# (unlinking a running script is safe: bash keeps the file open until it exits)
_cleanup_self() {
  if [[ -n "${P2P_UNINSTALL_COPIED:-}" && -f "${BASH_SOURCE[0]:-}" ]]; then
    case "${BASH_SOURCE[0]}" in
      */p2p-uninstall.*.sh) rm -f "${BASH_SOURCE[0]}" 2>/dev/null || true;;
    esac
  fi
}
trap _cleanup_self EXIT

# ── arg parse ──
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full)             MODE="full"; shift;;
    --keep-data|--keep) MODE="keep"; shift;;
    --dir)              INSTALL_DIR="$2"; shift 2;;
    --yes|-y)           ASSUME_YES=1; shift;;
    --help|-h)          usage; exit 0;;
    --)                 shift; break;;
    *) err "Unknown option: $1"; usage; exit 1;;
  esac
done

# ── prompts must work even when piped (curl | bash / wget | bash) ──
if [[ ! -t 0 ]]; then
  { exec < /dev/tty; } 2>/dev/null || true
fi
INTERACTIVE=0
[[ -t 0 ]] && INTERACTIVE=1

# ── helpers ──
looks_like_install() {
  [[ -d "$1" ]] || return 1
  [[ -f "$1/bot.py" || -f "$1/config.json" || -f "$1/data.json" || -d "$1/venv" ]]
}

detect_install_dir() {
  # 1. --dir flag
  if [[ -n "$INSTALL_DIR" ]]; then return 0; fi
  # 2. the systemd service knows it (WorkingDirectory=…)
  if [[ -f "$SERVICE_FILE" ]]; then
    local wd=""
    wd="$($SUDO grep -m1 '^WorkingDirectory=' "$SERVICE_FILE" 2>/dev/null | cut -d= -f2- || true)"
    if [[ -n "$wd" && -d "$wd" ]]; then
      INSTALL_DIR="$wd"
      return 0
    fi
  fi
  # 3. current directory
  if looks_like_install "$(pwd)"; then
    INSTALL_DIR="$(pwd)"
    return 0
  fi
  # 4. the script's own directory
  local sd=""
  sd="$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-.}")" 2>/dev/null && pwd || true)"
  if [[ -n "$sd" ]] && looks_like_install "$sd"; then
    INSTALL_DIR="$sd"
    return 0
  fi
  # 5. the usual default install locations
  local cand
  for cand in "/opt/p2p-bot" "$HOME/exchange" "$HOME/exchange-local" "$HOME/OKX_Telegram_P2P_Price_Bot"; do
    if looks_like_install "$cand"; then
      INSTALL_DIR="$cand"
      return 0
    fi
  done
  return 1
}

ask_what_to_remove() {
  echo ""
  echo -e "${BOLD}What should the uninstaller remove?${NC}"
  echo ""
  echo -e "  ${BOLD}1)${NC} Erase ${RED}EVERYTHING${NC} install.sh created"
  echo -e "     service · bot process · cron entry · venv · source code"
  echo -e "     ${RED}including config.json and data.json${NC}"
  echo ""
  echo -e "  ${BOLD}2)${NC} Keep my data — erase the rest"
  echo -e "     config.json + data.json (+ .env) are saved to a backup folder,"
  echo -e "     then service · bot process · cron · venv · source are removed"
  echo ""
  echo -e "  ${BOLD}3)${NC} Cancel — remove nothing"
  echo ""
  local answer=""
  while true; do
    if ! read -r -p "Choose [1/2/3]: " answer; then
      echo ""
      err "Input ended — cancelling, nothing was removed."
      exit 1
    fi
    case "$answer" in
      1) MODE="full"; return 0;;
      2) MODE="keep"; return 0;;
      3|q|Q|c|C) err "Cancelled — nothing was removed."; exit 1;;
      *) echo "  Please answer 1, 2 or 3.";;
    esac
  done
}

confirm() {  # confirm "question" → 0 on yes
  local answer=""
  if ! read -r -p "$1 [y/N]: " answer; then
    echo ""
    return 1
  fi
  [[ "$answer" =~ ^[Yy] ]]
}

# ── removal steps (each reverses one thing install.sh did) ──
remove_service() {
  if command -v systemctl >/dev/null 2>&1 && [[ -f "$SERVICE_FILE" ]]; then
    $SUDO systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    $SUDO systemctl disable "$SERVICE_NAME" 2>/dev/null || true
    $SUDO rm -f "$SERVICE_FILE"
    $SUDO systemctl daemon-reload 2>/dev/null || true
    $SUDO systemctl reset-failed "$SERVICE_NAME" 2>/dev/null || true
    ok "systemd service removed"
  else
    info "No systemd service found"
  fi
}

stop_processes() {
  local pidfile
  for pidfile in "${INSTALL_DIR:-.}/bot.pid" "./bot.pid"; do
    if [[ -f "$pidfile" ]]; then
      kill "$(cat "$pidfile")" 2>/dev/null || true
      rm -f "$pidfile"
    fi
  done
  if [[ -n "$INSTALL_DIR" ]]; then
    pkill -f "$INSTALL_DIR/bot.py" 2>/dev/null || true
  else
    pkill -f "bot\.py" 2>/dev/null || true
  fi
  ok "Bot process stopped (if it was running)"
}

clean_crontab() {  # clean_crontab [username] — drop the @reboot bot entry
  local user="${1:-}" list="" filtered=""
  command -v crontab >/dev/null 2>&1 || return 0
  if [[ -n "$user" ]]; then
    list="$($SUDO crontab -u "$user" -l 2>/dev/null || true)"
  else
    list="$(crontab -l 2>/dev/null || true)"
  fi
  [[ -n "$list" ]] || return 0
  if [[ -n "$INSTALL_DIR" ]]; then
    filtered="$(grep -v -F "$INSTALL_DIR/bot.py" <<<"$list" || true)"
  else
    filtered="$(grep -v "bot\.py" <<<"$list" || true)"
  fi
  [[ "$filtered" != "$list" ]] || return 0
  if [[ -z "$(tr -d '[:space:]' <<<"$filtered")" ]]; then
    # nothing left in the crontab — remove it entirely
    if [[ -n "$user" ]]; then $SUDO crontab -u "$user" -r 2>/dev/null || true
    else crontab -r 2>/dev/null || true; fi
  else
    if [[ -n "$user" ]]; then printf '%s\n' "$filtered" | $SUDO crontab -u "$user" - 2>/dev/null || true
    else printf '%s\n' "$filtered" | crontab - 2>/dev/null || true; fi
  fi
  ok "Cron @reboot entry removed${user:+ (user $user)}"
}

backup_data() {  # echoes the backup dir; rc 0 = saved, 2 = nothing to save, 1 = failed
  local dest_root="" dest f saved=0
  # keep the backup in the real user's home (not root's) when run with sudo
  if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]] && command -v getent >/dev/null 2>&1; then
    dest_root="$(getent passwd "$SUDO_USER" | cut -d: -f6 || true)"
  fi
  [[ -n "$dest_root" && -d "$dest_root" ]] || dest_root="$HOME"
  dest="$dest_root/p2p-bot-backup-$(date +%Y%m%d-%H%M%S)"
  if ! mkdir -p "$dest" 2>/dev/null; then
    err "Could not create backup dir $dest"
    return 1
  fi
  for f in config.json data.json config.json.bak .env; do
    if [[ -f "$INSTALL_DIR/$f" ]]; then
      cp -p "$INSTALL_DIR/$f" "$dest/" 2>/dev/null || true
      [[ -f "$dest/$f" ]] && saved=$((saved + 1)) || true
    fi
  done
  if [[ "$saved" -eq 0 ]]; then
    rmdir "$dest" 2>/dev/null || true
    return 2
  fi
  if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
    $SUDO chown -R "$SUDO_USER:$SUDO_USER" "$dest" 2>/dev/null || true
  fi
  echo "$dest"
  return 0
}

safe_to_wipe() {
  case "$INSTALL_DIR" in
    ""|"/"|"/usr"|"/etc"|"/var"|"/home"|"/opt"|"/root"|"/tmp"|"/bin"|*"/.."*|*".."*|".") return 1;;
  esac
  [[ ${#INSTALL_DIR} -ge 4 ]] || return 1
  looks_like_install "$INSTALL_DIR"
}

wipe_install_dir() {
  cd /    # never delete a directory we are standing in
  $SUDO rm -rf "$INSTALL_DIR"
}

# ─────────────────────────────────────────────────────────────
#  main
# ─────────────────────────────────────────────────────────────

echo -e "${YELLOW}Uninstalling $SERVICE_NAME ...${NC}"

if ! detect_install_dir; then
  warn "Could not find the install directory (no service, no ./bot.py, no usual location)."
  warn "Service / process / cron are still removed; pass --dir PATH to also remove the files."
fi

# ── decide what to remove ──
if [[ -z "$MODE" ]]; then
  if [[ $INTERACTIVE -eq 1 ]]; then
    [[ -n "$INSTALL_DIR" ]] && echo -e "  Install dir: ${BOLD}$INSTALL_DIR${NC}"
    ask_what_to_remove
  else
    MODE="keep"
    warn "No terminal — defaulting to KEEPING your data (config.json + data.json are backed up)."
    warn "Run again with --full to erase everything."
  fi
elif [[ $INTERACTIVE -eq 1 && $ASSUME_YES -eq 0 ]]; then
  # a mode flag was given, but confirm before deleting anything
  echo ""
  if [[ "$MODE" == "full" ]]; then
    echo -e "${BOLD}Mode:${NC} erase ${RED}EVERYTHING${NC}"
    [[ -n "$INSTALL_DIR" ]] && echo -e "  ${RED}rm -rf $INSTALL_DIR${NC}  (source, venv, config.json, data.json)"
  else
    echo -e "${BOLD}Mode:${NC} erase everything, save config.json + data.json to a backup folder"
    [[ -n "$INSTALL_DIR" ]] && echo -e "  ${RED}rm -rf $INSTALL_DIR${NC}  (json data is copied out first)"
  fi
  if [[ -n "$INSTALL_DIR" && -d "$INSTALL_DIR/.git" ]]; then
    warn "$INSTALL_DIR is a git repository checkout — it will be deleted."
  fi
  if ! confirm "Proceed?"; then
    err "Cancelled — nothing was removed."
    exit 1
  fi
fi

# ── 1. systemd service ──
step "1/4  Service"
remove_service

# ── 2. bot process ──
step "2/4  Bot process"
stop_processes

# ── 3. cron @reboot entry (added by the nohup fallback) ──
step "3/4  Cron"
if command -v crontab >/dev/null 2>&1; then
  clean_crontab            # the user who ran the uninstall
  [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]] && clean_crontab "$SUDO_USER" || true
  info "Cron checked (no @reboot bot entry left)."
else
  info "crontab not available — nothing to do."
fi

# ── 4. install directory ──
step "4/4  Files"
BACKUP_DIR=""
KEEP_STATUS="none"      # none | saved | inplace | wiped-all
if [[ -z "$INSTALL_DIR" ]]; then
  warn "Install directory unknown — no files removed from disk."
elif ! safe_to_wipe; then
  warn "Refusing to remove '$INSTALL_DIR' (does not look like a bot install, or unsafe path)."
  warn "Remove it manually if you really want to:  rm -rf $INSTALL_DIR"
elif [[ "$MODE" == "keep" ]]; then
  set +e
  BACKUP_DIR="$(backup_data)"
  _rc=$?
  set -e
  if [[ $_rc -eq 0 ]]; then
    ok "Data saved → $BACKUP_DIR"
    KEEP_STATUS="saved"
  elif [[ $_rc -eq 2 ]]; then
    info "No config.json / data.json found in $INSTALL_DIR — nothing to keep."
    KEEP_STATUS="none"
  else
    KEEP_STATUS="inplace"
    warn "Backup failed — leaving $INSTALL_DIR in place so nothing is lost."
    warn "Save your files, then remove the directory manually:  rm -rf $INSTALL_DIR"
  fi
  if [[ "$KEEP_STATUS" != "inplace" ]]; then
    wipe_install_dir
    ok "Install directory removed: $INSTALL_DIR"
  fi
else
  wipe_install_dir
  ok "Install directory removed: $INSTALL_DIR"
  KEEP_STATUS="wiped-all"
fi

# ── summary ──
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
if [[ "$MODE" == "full" ]]; then
  echo -e "${GREEN}${BOLD}  🗑  Fully uninstalled — everything erased.${NC}"
else
  echo -e "${GREEN}${BOLD}  🗑  Uninstalled — your data is safe.${NC}"
fi
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
if [[ "$MODE" == "keep" ]]; then
  case "$KEEP_STATUS" in
    saved)
      echo -e "  ${BOLD}Saved data:${NC} $BACKUP_DIR"
      echo -e "              config.json · data.json (+ .env / config.json.bak if they existed)"
      echo ""
      echo -e "  ${BOLD}To reinstall later:${NC}"
      echo -e "   1. run install.sh again (the same way you installed before)"
      echo -e "   2. copy the saved data into the new install dir:"
      echo -e "      cp $BACKUP_DIR/config.json $BACKUP_DIR/data.json <install-dir>/"
      ;;
    inplace)
      echo -e "  ${BOLD}Data:${NC} still in place in $INSTALL_DIR (backup failed — see warnings above)."
      ;;
    none)
      echo -e "  ${BOLD}Data:${NC} there was no config.json / data.json to save."
      ;;
  esac
else
  echo -e "  ${BOLD}Data:${NC} config.json and data.json were erased too."
fi
[[ -z "$INSTALL_DIR" && "$MODE" == "full" ]] && \
  warn "Install directory was unknown — check for leftovers manually (e.g. /opt/p2p-bot or ~/exchange)."
echo ""
echo -e "  ${DIM}apt packages (python3, pip, git, curl, wget, …) were left installed —"
echo -e "  other software on this machine may need them. Remove them manually with"
echo -e "  'sudo apt-get remove …' only if you are sure.${NC}"
echo ""
echo -e "${GREEN}Done.${NC}"
