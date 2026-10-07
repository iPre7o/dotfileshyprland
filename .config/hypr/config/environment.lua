-- See https://wiki.hypr.land/Configuring/Advanced-and-Cool/Environment-variables/

hl.env("XCURSOR_SIZE", "24")
hl.env("HYPRCURSOR_SIZE", "24")

-- Forca apps Qt (Dolphin, Ark - Qt6/KF6) a usarem a integracao nativa do KDE (le kdeglobals)
hl.env("QT_QPA_PLATFORMTHEME", "kde")
