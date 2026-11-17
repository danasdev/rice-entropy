#!/usr/bin/env bash
# Fixa o Hyprland (e as libs irmãs) numa versão que ainda lê hyprland.conf (hyprlang).
# A partir da 0.55 o Hyprland passou a usar hyprland.lua e, segundo relatos, a 0.57 removeu o .conf.
# A rice é escrita em hyprlang, então este script instala a última versão ANTES da 0.55
# a partir do Arch Linux Archive e põe os pacotes em IgnorePkg (para o pacman -Syu não atualizar).
#
# Uso:  tools/pin-hyprland.sh            # usa a última 0.54.x
#       tools/pin-hyprland.sh 0.54.2     # força uma versão exata do hyprland
#       tools/pin-hyprland.sh --dry-run  # só mostra o que faria
#       tools/pin-hyprland.sh --snapshot # RECOMENDADO: volta o sistema inteiro para a data da versão
#                                        # certa (snapshot do Arch Archive), assim nenhuma lib fica desalinhada
set -euo pipefail

ARCHIVE="https://archive.archlinux.org/packages"
# Libs que precisam ser da mesma época do hyprland (só as que estiverem instaladas são trocadas).
LIBS=(hyprutils hyprlang hyprcursor hyprgraphics aquamarine hyprland-protocols hyprwayland-scanner hyprwire xdg-desktop-portal-hyprland hyprland-qt-support hyprland-qtutils hyprpolkitagent hyprlock hypridle libjxl highway)
say() { printf '\n\033[1;35m==> %s\033[0m\n' "$*"; }
die() { echo "ERRO: $*" >&2; exit 1; }

DRY=0; SNAP=0; WANT=""
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --snapshot) SNAP=1 ;;
    [0-9]*) WANT="$a" ;;
    *) die "argumento desconhecido: $a" ;;
  esac
done

[ "$EUID" -ne 0 ] || die "Rode como o seu usuário (usa sudo)."
command -v pacman >/dev/null || die "Só para Arch Linux."
command -v curl >/dev/null || sudo pacman -S --needed --noconfirm curl

# Lista "arquivo<TAB>epoch" dos pacotes x86_64 de um nome no archive.
list_pkg() {
  local name="$1" first="${1:0:1}"
  curl -fsS "$ARCHIVE/$first/$name/" |
    sed -nE "s/.*href=\"($name-[0-9][^\"]*-(x86_64|any)\.pkg\.tar\.zst)\".*([0-9]{2}-[A-Za-z]{3}-[0-9]{4} [0-9]{2}:[0-9]{2}).*/\1\t\3/p" |
    while IFS=$'\t' read -r f d; do printf '%s\t%s\n' "$f" "$(date -u -d "${d//-/ }" +%s)"; done
}
ver_of() { sed -E "s/^$1-(.*)-(x86_64|any)\.pkg\.tar\.zst$/\1/" <<<"$2"; }

say "Procurando o hyprland no Arch Linux Archive"
mapfile -t HL < <(list_pkg hyprland | sort -t$'\t' -k1,1V)
[ "${#HL[@]}" -gt 0 ] || die "não consegui listar $ARCHIVE/h/hyprland/ (sem rede ou o host está bloqueado)."

PICK=""
for line in "${HL[@]}"; do
  f="${line%%$'\t'*}"; v="$(ver_of hyprland "$f")"; vv="${v%-*}"
  if [ -n "$WANT" ]; then
    [[ "$vv" == "$WANT" ]] && PICK="$line"
  else
    # última versão < 0.55
    if [[ "$vv" =~ ^0\.([0-9]+)\. ]] && [ "${BASH_REMATCH[1]}" -lt 55 ]; then PICK="$line"; fi
  fi
done
[ -n "$PICK" ] || die "nenhuma versão adequada do hyprland encontrada${WANT:+ ($WANT)}."
HFILE="${PICK%%$'\t'*}"; HTIME="${PICK##*$'\t'}"
echo "hyprland alvo: $HFILE ($(date -u -d @"$HTIME" +%F))"

if [ "$SNAP" -eq 1 ]; then
  D="$(date -u -d @"$HTIME" +%Y/%m/%d)"
  SERVER="https://archive.archlinux.org/repos/$D/\$repo/os/\$arch"
  say "Snapshot do Arch Archive de $D"
  echo "Server = $SERVER"
  if [ "$DRY" -eq 1 ]; then echo "(dry-run: nada foi alterado)"; exit 0; fi
  echo "Isso volta o SISTEMA INTEIRO (todos os pacotes) para essa data. Feche tudo que for importante."
  read -r -p "Continuar? [s/N] " ans; [[ "$ans" =~ ^[sSyY]$ ]] || die "cancelado."
  sudo cp -n /etc/pacman.d/mirrorlist /etc/pacman.d/mirrorlist.bak-rice
  printf 'Server = %s\n' "$SERVER" | sudo tee /etc/pacman.d/mirrorlist >/dev/null
  # o archive é lento: sem isso o pacman desiste de um arquivo por timeout
  grep -qE '^\s*DisableDownloadTimeout' /etc/pacman.conf || sudo sed -i '/^\[options\]/a DisableDownloadTimeout' /etc/pacman.conf
  sudo pacman -Syyuu || die "o pacman falhou. Para desfazer: sudo cp /etc/pacman.d/mirrorlist.bak-rice /etc/pacman.d/mirrorlist"
  INST="$(pacman -Q hyprland | awk '{print $2}')"
  echo "hyprland instalado: $INST"
  if [[ "$INST" =~ ^0\.([0-9]+)\. ]] && [ "${BASH_REMATCH[1]}" -ge 55 ]; then
    die "o snapshot de $D ainda trouxe $INST. Rode de novo com uma versão exata (ex.: tools/pin-hyprland.sh --snapshot 0.54.0)."
  fi
  if [ -f "$HOME/.config/hypr/hyprland.lua" ]; then
    mv "$HOME/.config/hypr/hyprland.lua" "$HOME/.config/hypr/hyprland.lua.bak-rice"
  fi
  echo
  echo "Pronto. O sistema está congelado em $D (o mirrorlist agora aponta para o archive)."
  echo "REINICIE o PC (o kernel pode ter mudado) e entre no Hyprland."
  echo "Para voltar ao normal um dia: sudo cp /etc/pacman.d/mirrorlist.bak-rice /etc/pacman.d/mirrorlist  e  sudo pacman -Syyu"
  exit 0
fi

# libs do sistema (ex.: libjxl) que o hyprgraphics antigo exige numa versão mais velha: os pacotes
# instalados que dependem delas precisam voltar junto, senão o pacman recusa o conjunto.
for base in libjxl highway; do
  pacman -Qq "$base" >/dev/null 2>&1 || continue
  for r in $(LC_ALL=C pacman -Qi "$base" | awk -F': ' '/^Required By/{print $2}'); do
    [ "$r" = None ] && continue
    case " ${LIBS[*]} " in *" $r "*) ;; *) LIBS+=("$r") ;; esac
  done
done

TARGETS=("hyprland|$HFILE")
for lib in "${LIBS[@]}"; do
  pacman -Qq "$lib" >/dev/null 2>&1 || continue
  # versão mais nova do pacote que ainda era a atual na data do hyprland alvo
  best=""
  while IFS=$'\t' read -r f t; do
    [ "$t" -le "$HTIME" ] && best="$f"
  done < <(list_pkg "$lib" | sort -t$'\t' -k2,2n)
  [ -n "$best" ] || { echo "aviso: sem versão antiga de $lib; mantendo a atual."; continue; }
  echo "$lib -> $best"
  TARGETS+=("$lib|$best")
done

if [ "$DRY" -eq 1 ]; then echo; echo "(dry-run: nada foi instalado)"; exit 0; fi

say "Baixando"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
FILES=(); NAMES=()
for t in "${TARGETS[@]}"; do
  name="${t%%|*}"; f="${t##*|}"
  curl -fL --progress-bar -o "$TMP/$f" "$ARCHIVE/${name:0:1}/$name/$f"
  FILES+=("$TMP/$f"); NAMES+=("$name")
done

say "Instalando (downgrade)"
sudo pacman -U --noconfirm "${FILES[@]}" ||
  die "o pacman recusou o conjunto. Rode com --dry-run, confira as versões e, se preciso, passe outra versão do hyprland (ex.: tools/pin-hyprland.sh 0.54.0)."

say "Travando as versões (IgnorePkg)"
CUR="$(grep -E '^\s*IgnorePkg' /etc/pacman.conf || true)"
ADD=()
for n in "${NAMES[@]}"; do grep -qE "^\s*IgnorePkg.*\b$n\b" /etc/pacman.conf || ADD+=("$n"); done
if [ "${#ADD[@]}" -gt 0 ]; then
  if [ -n "$CUR" ]; then
    sudo sed -i -E "s|^\s*(IgnorePkg\s*=.*)$|\1 ${ADD[*]}|" /etc/pacman.conf
  else
    sudo sed -i -E "/^\[options\]/a IgnorePkg = ${ADD[*]}" /etc/pacman.conf
  fi
fi

# O Hyprland novo cria um hyprland.lua sozinho; com ele a rice (hyprland.conf) é ignorada.
if [ -f "$HOME/.config/hypr/hyprland.lua" ]; then
  mv "$HOME/.config/hypr/hyprland.lua" "$HOME/.config/hypr/hyprland.lua.bak-rice"
  echo "hyprland.lua renomeado para hyprland.lua.bak-rice"
fi

echo
echo "Pronto: $(pacman -Q hyprland). Reinicie (ou: pkill -x Hyprland) e entre de novo no Hyprland."
echo "Para destravar no futuro: remova esses pacotes de IgnorePkg em /etc/pacman.conf."
