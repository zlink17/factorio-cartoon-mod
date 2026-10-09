-- Remplace les chemins de textures du jeu par leur version cartoon.
-- manifest.lua (généré par tools/build_manifest.py) liste les textures refaites,
-- stockées sous graphics/overrides/<mod>/ avec le même chemin que l'original.
-- Exemple : ["__base__/graphics/x.png"] = true

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
    elseif (key == "filename" or key == "icon") and type(value) == "string" then
      tbl[key] = remap(value)
    end
  end
end

walk(data.raw)

-- Cadrage des assembleurs 1 à 3 : nos planches ne font pas la taille des originales.
-- Images de 224 x 272 px (pixel art x4), planche 8 x 4 de 32 images. scale 0.5 : 1 px d'art = 2 px de jeu,
-- donc 16 px d'art par case. L'ombre est cuite dans son image (même cadre que le sprite, décalage identique).
local FRAME = { width = 224, height = 272, scale = 0.5, shift = { 0, -0.25 } }

for n = 1, 3 do
  local proto = data.raw["assembling-machine"]["assembling-machine-" .. n]
  local layers = proto and proto.graphics_set and proto.graphics_set.animation and proto.graphics_set.animation.layers
  if layers then
    for i, layer in ipairs(layers) do
      layer.width, layer.height, layer.scale = FRAME.width, FRAME.height, FRAME.scale
      layer.shift = { FRAME.shift[1], FRAME.shift[2] }
      if i == 1 then
        layer.frame_count, layer.line_length, layer.repeat_count = 32, 8, nil
      else
        layer.frame_count, layer.line_length, layer.repeat_count = 1, 1, 32
      end
    end
  end
end
