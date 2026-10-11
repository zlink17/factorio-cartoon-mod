-- Parties existantes : retire les décorations triées (herbes, cailloux...) générées dans l'emprise d'un gros
-- rocher, qui passeraient devant lui. Les nouveaux morceaux de carte n'en reçoivent plus (masque de collision des
-- rochers, data-final-fixes.lua). Les taches au sol, dessinées dessous, sont gardées.
local sorted = require("__factorio-cartoon-mod__/sorted_decoratives")

local rocks, removed = 0, 0
for _, surface in pairs(game.surfaces) do
  for _, rock in pairs(surface.find_entities_filtered { name = sorted.rocks }) do
    local area = rock.bounding_box
    rocks = rocks + 1
    removed = removed + #surface.find_decoratives_filtered { area = area, name = sorted.decoratives }
    surface.destroy_decoratives { area = area, name = sorted.decoratives }
  end
end
log(string.format("mod cartoon : %d décorations retirées sous %d gros rochers", removed, rocks))
