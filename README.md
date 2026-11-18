# rice-entropy

Uma rice para **Arch Linux + Hyprland** baseada no shell [Noctalia](https://github.com/noctalia-dev/noctalia), com vidro de verdade (refração e blur), um painel de controle próprio, uma "ilha" no topo, menu de apps, ícones redesenhados e cores que acompanham o papel de parede.

> Feito e testado em um notebook Intel com um monitor externo. Os monitores, o teclado (ABNT2) e a localização precisam ser ajustados para a sua máquina (veja "Depois de instalar").

## O que tem

- **Vidro:** o plugin [hyprglass](https://github.com/hyprnux/hyprglass) aplica refração e blur no kitty, na barra, no dock e nos widgets. Um script mede o brilho do papel de parede e escurece ou clareia o vidro sozinho, para o texto sempre ficar legível.
- **Painel de controle (Super+S):** Wi-Fi, Bluetooth, volume, brilho, mídia, notificações, energia, rede, calendário, clima, papel de parede e sessão, tudo dentro do próprio painel. Abre com uma animação de líquido saindo do topo.
- **Dock (embaixo):** ilha própria que sai de baixo da tela e se expande no menu de apps (um objeto só).
- **Ilha (topo):** pílula com hora e bateria, ligada à borda do topo por uma forma líquida. Some quando há janelas abertas e aparece na área de trabalho vazia ou ao passar o mouse no topo; clicar abre o painel.
- **Menu de apps (Super+Espaço):** busca, grade/lista, recentes, categorias, calculadora (`=`), executar comando (`>`), busca na web e histórico da área de transferência.
- **Ícones Entropy:** tema gerado a partir das logos reais dos apps, recoloridas em um tom só da paleta do papel de parede.
- **Minimizar com fade (Super+M),** gaveta de minimizadas, snap de janelas e capturas de tela/gravação.

## Instalação (Arch)

A instalação tem **duas fases**: a do sistema (pacotes e arquivos) e a de dentro do Hyprland (plugin de vidro e ícones), porque o `hyprpm` só funciona com o Hyprland rodando.

### Opção A: já no archinstall (recomendada)

Na live ISO, com internet, rode o archinstall apontando para a lista de pacotes deste repositório. Ele instala tudo junto com o sistema e continua perguntando disco, usuário, idioma e o resto normalmente:

```bash
archinstall --config-url https://raw.githubusercontent.com/danasdev/rice-entropy/main/archinstall.json
```

Escolha um perfil mínimo (ou o perfil Hyprland), crie seu usuário com `sudo` e instale. Depois do primeiro boot, no TTY:

```bash
curl -fsSL https://raw.githubusercontent.com/danasdev/rice-entropy/main/bootstrap.sh | bash
```

> **Abriu direto no Hyprland e não achou o TTY?** Dá para rodar tudo por dentro: abra um terminal (no Hyprland puro o atalho é `Super+Q`) e use o comando acima. Se preferir um TTY, é `Ctrl+Alt+F3` (de F2 a F6); `Ctrl+Alt+F1` ou `F2` volta para a tela gráfica. Rodando por dentro, depois do `setup-plugins.sh` saia e entre de novo no Hyprland (ou reinicie) para a rice subir inteira.

### Opção B: sistema Arch que já existe

O mesmo comando do `bootstrap.sh` serve: ele instala o `git` se faltar, clona o repositório em `~/rice-entropy` e roda o instalador.

### O que o instalador faz

1. Instala os pacotes de `packages/pacman.txt` (`--needed`, então o que já veio do archinstall é ignorado).
2. Ativa os serviços: NetworkManager, bluetooth, power-profiles-daemon e upower.
3. Faz **backup** de `~/.config/{hypr,kitty,noctalia}` em `~/.config-backup-rice-<data>` e copia as configs do repositório, trocando o marcador `@HOME@` pelo seu diretório.
4. Coloca um papel de parede padrão em `~/Pictures/Wallpapers` e grava seu nome para a saudação do painel.

### Fase dentro do Hyprland

Reinicie, entre no Hyprland (escolha "Hyprland" no login ou rode `Hyprland` no TTY) e, em um terminal (`Super+Enter`):

```bash
~/rice-entropy/setup-plugins.sh
```

Ele compila o plugin hyprglass pelo `hyprpm`, gera o tema de ícones com a paleta do papel de parede e recarrega a sessão.

### AUR (opcional)

O `yay` não vem pelo archinstall. Para apps do AUR depois: `git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si`. Nenhum pacote do AUR é obrigatório para a rice.

## Se abrir o Hyprland padrão mesmo depois de instalar

O Hyprland escolhe **na abertura** qual configuração usar e dá prioridade a um `~/.config/hypr/hyprland.lua` sobre o `hyprland.conf` da rice. Se existir um `.lua` (algumas versões o geram na primeira execução), a rice é ignorada. Renomeie e **reabra a sessão** (`hyprctl reload` não basta, porque ele continua procurando o `.lua`):

```bash
mv ~/.config/hypr/hyprland.lua ~/.config/hypr/hyprland.lua.bak
pkill -x Hyprland        # ou reinicie (em modo Lua o `hyprctl dispatch exit` não funciona)
```

## Hyprland novo demais (erro "lua config error" / `unexpected symbol near '#'`)

A rice é escrita em `hyprland.conf` (hyprlang). A partir do Hyprland 0.55 o formato principal é `hyprland.lua` e, segundo relatos, a 0.57 removeu o `.conf`. Nessas versões o Hyprland gera um `hyprland.lua` sozinho a cada abertura, e forçar o `.conf` faz ele ler o arquivo como Lua (erro no `#` da linha 2). O `install.sh` já detecta isso e chama o script abaixo, mas dá para rodar à mão (num TTY, `Ctrl+Alt+F3`):

```bash
~/rice-entropy/tools/pin-hyprland.sh --snapshot  # RECOMENDADO: volta o sistema todo para a data certa (sem dependências quebradas)
~/rice-entropy/tools/pin-hyprland.sh --dry-run   # mostra as versões que vai usar
~/rice-entropy/tools/pin-hyprland.sh             # instala a última 0.54.x e trava em IgnorePkg
~/rice-entropy/tools/pin-hyprland.sh 0.54.2      # ou uma versão específica
```

Ele baixa do Arch Linux Archive o `hyprland` e as libs irmãs (`hyprutils`, `hyprlang`, `aquamarine`...) da mesma época, instala com `pacman -U`, coloca todos em `IgnorePkg` (o `pacman -Syu` não os atualiza) e renomeia o `hyprland.lua`. Para destravar no futuro, remova esses pacotes de `IgnorePkg` em `/etc/pacman.conf`.

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
python3 tools/export.py   # também regenera o archinstall.json a partir de packages/pacman.txt
git add -A && git commit -m "atualiza a rice" && git push
```

## Créditos

- [Noctalia](https://github.com/noctalia-dev/noctalia) (shell) e [hyprglass](https://github.com/hyprnux/hyprglass) (vidro).
- Papirus (base dos ícones de sistema), Inter e JetBrains Mono Nerd Font.
