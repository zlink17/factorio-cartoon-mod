-- Une densité par famille, en pourcentage de la densité d'origine (100 = comme le jeu, 0 = aucune).
local defaults = { herbes = 0, plantes = 0, cailloux = 0, taches = 30 }
local order = { herbes = "a", plantes = "b", cailloux = "c", taches = "d" }

for family, value in pairs(defaults) do
  data:extend({ {
    type = "int-setting",
    name = "cartoon-epure-" .. family,
    setting_type = "startup",
    default_value = value,
    minimum_value = 0,
    maximum_value = 100,
    order = order[family],
  } })
end
