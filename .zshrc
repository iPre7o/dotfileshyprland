# --- básico (equivalente ao que você já tinha no .bashrc) ---
alias ls='ls --color=auto'
alias grep='grep --color=auto'
export PATH="$HOME/.local/bin:$PATH"

# prompt parecido com o do bash
PROMPT='%B%F{white}%n@%m%f%b %B%F{white}%1~%f%b '

# histórico
HISTFILE=~/.zsh_history
HISTSIZE=5000
SAVEHIST=5000
setopt SHARE_HISTORY

# autocomplete básico do zsh
autoload -Uz compinit && compinit

# --- plugins ---
source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh

fastfetch
