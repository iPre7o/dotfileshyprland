#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='\[\e[1;37m\]\u@\h\[\e[0m\] \[\e[1;37m\]\[\e[0m\] \[\e[1;37m\]\W\[\e[0m\] '
export PATH="$HOME/.local/bin:$PATH"

fastfetch
