-- Densité des décorations par famille, en pourcentage de celle du jeu (100 = comme le jeu, 0 = aucune).
-- Le pixel art supporte mal la profusion de détails du jeu d'origine : départ à 10 %, à juger en jeu.
local defaults = { herbes = 10, plantes = 10, cailloux = 10, taches = 10 }
local order = { herbes = "a", plantes = "b", cailloux = "c", taches = "d" }

for family, value in pairs(defaults) do
  data:extend({ {
    type = "int-setting",
    name = "pixel-decorations-" .. family,
    setting_type = "startup",
    default_value = value,
    minimum_value = 0,
    maximum_value = 100,
    order = order[family],
  } })
end
