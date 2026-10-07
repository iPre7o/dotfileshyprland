#!/usr/bin/env bash
# Roda um comando forcando o uso da GPU dedicada NVIDIA via PRIME render
# offload (util em notebooks hibridos AMD/NVIDIA, ex: Steam e jogos).
#
# So funciona depois que o driver de kernel da NVIDIA estiver instalado e
# carregado (verifique com `nvidia-smi` antes de usar).
#
# Uso: nvidia-offload.sh <comando> [args...]
set -euo pipefail

export __NV_PRIME_RENDER_OFFLOAD=1
export __NV_PRIME_RENDER_OFFLOAD_PROVIDER=NVIDIA-G0
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __VK_LAYER_NV_optimus=NVIDIA_only

exec "$@"
