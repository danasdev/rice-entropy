# rice-entropy

Uma rice para **Arch Linux + Hyprland** baseada no shell [Noctalia](https://github.com/noctalia-dev/noctalia), com vidro de verdade (refração e blur), um painel de controle próprio, uma "ilha" no topo, menu de apps, ícones redesenhados e cores que acompanham o papel de parede.

> Feito e testado em um notebook Intel com um monitor externo. Os monitores, o teclado (ABNT2) e a localização precisam ser ajustados para a sua máquina (veja "Depois de instalar").

## O que tem

- **Vidro:** o plugin [hyprglass](https://github.com/hyprnux/hyprglass) aplica refração e blur no kitty, na barra, no dock e nos widgets. Um script mede o brilho do papel de parede e escurece ou clareia o vidro sozinho, para o texto sempre ficar legível.
- **Painel de controle (Super+S):** Wi-Fi, Bluetooth, volume, brilho, mídia, notificações, energia, rede, calendário, clima, papel de parede e sessão, tudo dentro do próprio painel. Abre com uma animação de líquido saindo do topo.
- **Ilha (topo):** pílula com hora e bateria, ligada à borda do topo por uma forma líquida. Some quando há janelas abertas e aparece na área de trabalho vazia ou ao passar o mouse no topo; clicar abre o painel.
- **Menu de apps (Super+Espaço):** busca, grade/lista, recentes, categorias, calculadora (`=`), executar comando (`>`), busca na web e histórico da área de transferência.
- **Ícones Entropy:** tema gerado a partir das logos reais dos apps, recoloridas em um tom só da paleta do papel de parede.
- **Minimizar com fade (Super+M),** gaveta de minimizadas, snap de janelas e capturas de tela/gravação.

## Instalação (Arch)

No `archinstall`, escolha um perfil mínimo (ou o perfil Hyprland), crie seu usuário com `sudo`, ative o `multilib` se for usar Steam e deixe estes pacotes em "Additional packages": `git base-devel`. O resto o instalador cuida.

Depois do primeiro boot, no TTY:

```bash
git clone https://github.com/danasdev/rice-entropy.git
cd rice-entropy
./install.sh
```

Reinicie, entre no Hyprland e, dentro dele:

```bash
./setup-plugins.sh
```

O `install.sh` instala os pacotes de `packages/pacman.txt`, ativa os serviços (NetworkManager, bluetooth, power-profiles-daemon, upower), faz **backup** de `~/.config/{hypr,kitty,noctalia}` antes de copiar as configs e coloca um papel de parede padrão. O `setup-plugins.sh` compila o hyprglass pelo `hyprpm` (precisa estar dentro do Hyprland) e gera o tema de ícones.

### AUR (opcional)

O `yay` não vem pelo archinstall. Para instalar apps do AUR depois:

```bash
git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si
```

Nenhum pacote do AUR é obrigatório para a rice.

## Depois de instalar

- **Monitores:** edite `~/.config/hypr/rice/monitors.conf` (use `hyprctl monitors`). Há um exemplo de duas telas em `monitors.exemplo-autor.conf`. Nos widgets de `~/.config/noctalia/config.toml`, troque os `output = "..."` pelos nomes dos seus monitores.
- **Teclado:** o layout está em `~/.config/hypr/rice/input.conf` (padrão ABNT2). Troque `kb_layout` se precisar.
- **Nome na saudação do painel:** `~/.config/entropy-name`.
- **Papéis de parede:** coloque imagens em `~/Pictures/Wallpapers`. Troque com Super+N (aleatório) ou pela página de papel de parede do painel (Super+S).
- **GPU NVIDIA:** instale `nvidia-open` e adicione as variáveis de ambiente do Hyprland para NVIDIA em `rice/env.conf`.

## Atalhos principais

| Atalho | Ação |
|---|---|
| `Super+Enter` | terminal (kitty) |
| `Super+Espaço` | menu de apps |
| `Super+S` | painel de controle |
| `Super+Alt+S` / `Super+Alt+Espaço` | painel e menu originais do Noctalia |
| `Super+Q` | fechar janela |
| `Super+M` / `Super+Shift+M` | minimizar / restaurar |
| `Super+Setas` | encaixar janela nas metades da tela |
| `Super+F` | tela cheia |
| `Super+L` | bloquear |
| `Alt+Tab` | trocar de janela |
| `Super+1..9` | workspaces |
| `Print` / `Super+Print` | captura de área / tela |

Todos os atalhos estão em `config/hypr/rice/binds.conf`.

## Plugin opcional: HyprWindowShade

A animação de abrir/fechar janelas (fade e "sucção") e o papel de parede animado usam o plugin HyprWindowShade, que **não está incluído** neste repositório. Sem ele tudo funciona normalmente, só sem esses dois efeitos. Se você tiver o plugin: copie o `.so` para `~/.local/share/hyprland/plugins/HyprWindowShade.so` e descomente a linha `source = ~/.config/hypr/windowshade.conf` em `~/.config/hypr/hyprland.conf`. Os shaders estão em `config/hypr/shaders`.

## Manter o repositório

Quem mantém a rice exporta do sistema para o repositório, já sem dados pessoais:

```bash
python3 tools/export.py
git add -A && git commit -m "atualiza a rice" && git push
```

## Créditos

- [Noctalia](https://github.com/noctalia-dev/noctalia) (shell) e [hyprglass](https://github.com/hyprnux/hyprglass) (vidro).
- Papirus (base dos ícones de sistema), Inter e JetBrains Mono Nerd Font.
