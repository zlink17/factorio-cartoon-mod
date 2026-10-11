-- Remplace les chemins de textures du jeu par leur version pixel art.
-- manifest.lua (généré par tools/build_manifest.py) liste les textures refaites,
-- stockées sous graphics/overrides/<mod>/ avec le même chemin que l'original.
-- Exemple : ["__base__/graphics/x.png"] = true
-- Les images ont la taille des originales (contrat du mod, docs/pixel/plan.md) : aucune correction de taille ici.

local MOD = "__factorio-pixel-mod__"
local manifest = require("manifest")

local visited = {}

local function remap(path)
  if manifest[path] then
    -- "__base__/graphics/x.png" -> "__factorio-pixel-mod__/graphics/overrides/base/x.png"
    local mod, rest = path:match("^__(.-)__/graphics/(.+)$")
    if mod and rest then
      return MOD .. "/graphics/overrides/" .. mod .. "/" .. rest
    end
  end
  return path
end

local function walk(tbl)
  if visited[tbl] then return end
  visited[tbl] = true
  for key, value in pairs(tbl) do
    if type(value) == "table" then
      walk(value)
    elseif type(value) == "string" then
      tbl[key] = remap(value)
    end
  end
end

-- Moins de décorations : la probabilité de génération de chaque décoration est multipliée par la densité réglée
-- pour sa famille (settings.lua). Les zones où elle apparaît restent les mêmes, elle y est seulement plus rare.
-- Ne touche que la génération : une carte déjà créée garde ses décorations (commande /pixel-decorations).
for family, names in pairs(require("decoratives")) do
  local factor = settings.startup["pixel-decorations-" .. family].value / 100
  for _, name in pairs(names) do
    local decorative = data.raw["optimized-decorative"][name]
    local autoplace = decorative and decorative.autoplace
    if autoplace and autoplace.probability_expression and factor < 1 then
      autoplace.probability_expression = "(" .. autoplace.probability_expression .. ") * " .. factor
    end
  end
end

walk(data.raw)
