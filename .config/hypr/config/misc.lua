hl.config({
    misc = {
        force_default_wallpaper = -1,    -- Set to 0 or 1 to disable the anime mascot wallpapers
        disable_hyprland_logo   = false, -- If true disables the random hyprland logo / anime girl background. :(
    },
})

-- Corrige fontes borradas em apps X11/XWayland (jgmenu, rofi, etc.) com escala fracionada (1.5x)
hl.config({
    xwayland = {
        force_zero_scaling = true,
    },
})
