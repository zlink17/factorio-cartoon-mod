-- Moins de décorations : la probabilité de génération de chaque décoration est multipliée par la densité réglée
-- pour sa famille. Les zones où elle apparaît restent les mêmes (mêmes bruits), elle y est seulement plus rare.
-- Ne touche que la génération : une carte déjà créée garde ses décorations (commande /cartoon-epure, control.lua).
local families = require("decoratives")

for family, names in pairs(families) do
  local factor = settings.startup["cartoon-epure-" .. family].value / 100
  for _, name in pairs(names) do
    local decorative = data.raw["optimized-decorative"][name]
    local autoplace = decorative and decorative.autoplace
    if autoplace and autoplace.probability_expression and factor < 1 then
      autoplace.probability_expression = "(" .. autoplace.probability_expression .. ") * " .. factor
    end
  end
end
