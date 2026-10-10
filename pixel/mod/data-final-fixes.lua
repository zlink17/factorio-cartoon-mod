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
    elseif (key == "filename" or key == "icon" or key == "picture" or key == "spritesheet") and type(value) == "string" then
      tbl[key] = remap(value)
    end
  end
end

walk(data.raw)

-- Cadrage des assembleurs 1 à 3 : nos planches ne font pas la taille des originales.
-- Images de 224 x 272 px (pixel art x4), planche 8 x 4 de 32 images. scale 0.5 : 1 px d'art = 2 px de jeu,
-- donc 16 px d'art par case. L'ombre est cuite dans sa planche (même cadre et même décalage que le sprite, une image par image).
local FRAME = { width = 224, height = 272, scale = 0.5, shift = { 0, -0.25 } }

for n = 1, 3 do
  local proto = data.raw["assembling-machine"]["assembling-machine-" .. n]
  local layers = proto and proto.graphics_set and proto.graphics_set.animation and proto.graphics_set.animation.layers
  if layers then
    for _, layer in ipairs(layers) do
      layer.width, layer.height, layer.scale = FRAME.width, FRAME.height, FRAME.scale
      layer.shift = { FRAME.shift[1], FRAME.shift[2] }
      layer.frame_count, layer.line_length, layer.repeat_count = 32, 8, nil
    end
  end
end

-- Inserters : tige et mains à 1 px d'art = 2 px de jeu (échelle 0,25 conservée, images x8), plateforme x4 (échelle 0,5).
-- Seules les tailles changent ; les ombres des mains sont communes (celles du burner).
local HAND_SIZES = {
  hand_base_picture = { 32, 136 }, hand_base_shadow = { 32, 136 },
  hand_closed_picture = { 72, 168 }, hand_closed_shadow = { 72, 168 },
  hand_open_picture = { 72, 168 }, hand_open_shadow = { 72, 168 },
}
-- (le stack-inserter de Space Age réutilise l'ombre de la tige du burner, seule sa hauteur change)
local stack = data.raw["inserter"]["stack-inserter"]
if stack and stack.hand_base_shadow then stack.hand_base_shadow.height = 136 end

for _, name in ipairs({ "inserter", "fast-inserter", "long-handed-inserter", "burner-inserter", "bulk-inserter" }) do
  local proto = data.raw["inserter"][name]
  if proto then
    local sizes = HAND_SIZES
    if name == "bulk-inserter" then   -- mains plus larges : ouverte 128 px, fermée 96 px
      sizes = {
        hand_base_picture = { 32, 136 }, hand_base_shadow = { 32, 136 },
        hand_closed_picture = { 96, 168 }, hand_closed_shadow = { 96, 168 },
        hand_open_picture = { 128, 168 }, hand_open_shadow = { 128, 168 },
      }
    end
    for key, size in pairs(sizes) do
      if proto[key] then proto[key].width, proto[key].height = size[1], size[2] end
    end
    local sheet = proto.platform_picture and proto.platform_picture.sheet
    if sheet then
      sheet.width, sheet.height = 104, 80
      sheet.shift = util.by_pixel(1.5, 1)
    end
  end
end

-- Répartiteurs : une image de 160 x 104 (nord, sud) ou 104 x 160 (est, ouest), 32 images en planche 8 x 4. Le motif est
-- centré sur l'entité et l'ombre est cuite dans l'image ; les pièces annexes de l'original ne servent plus.
local SPLITTER_FRAME = {
  north = { 160, 104 }, south = { 160, 104 }, east = { 104, 160 }, west = { 104, 160 },
}
-- Le lane-splitter réutilise les sprites du répartiteur de base.
for _, entry in ipairs({ { "splitter", "splitter" }, { "splitter", "fast-splitter" }, { "splitter", "express-splitter" }, { "splitter", "turbo-splitter" },
                         { "lane-splitter", "lane-splitter" } }) do
  local proto = data.raw[entry[1]] and data.raw[entry[1]][entry[2]]
  if proto and proto.structure then
    for dir, size in pairs(SPLITTER_FRAME) do
      local s = proto.structure[dir]
      s.width, s.height, s.shift = size[1], size[2], { 0, 0 }
      s.frame_count, s.line_length, s.scale = 32, 8, 0.5
    end
    proto.structure_patch = { north = util.empty_sprite(), east = util.empty_sprite(),
                              south = util.empty_sprite(), west = util.empty_sprite() }
  end
end

-- Poteaux électriques : 4 rotations par image, ombre séparée ; les points d'attache des câbles (cuivre, rouge, vert)
-- sont recalculés pour chaque variante d'après la position des isolateurs dessinés (poles_data.lua, généré).
local poles = require("poles_data")
for name, spec in pairs(poles) do
  local proto = data.raw["electric-pole"][name]
  local layers = proto and proto.pictures and proto.pictures.layers
  if layers then
    for i, layer in ipairs(layers) do
      local g = (i == 1) and spec.picture or spec.shadow
      layer.width, layer.height, layer.scale = g.width, g.height, 0.5
      layer.shift = util.by_pixel(g.shift[1], g.shift[2])
      layer.direction_count = 4
    end
    local function p(v) return util.by_pixel(v[1], v[2]) end
    proto.connection_points = {}
    for _, w in ipairs(spec.wires) do
      local c = { wire = {}, shadow = {} }
      for color, v in pairs(w.wire) do c.wire[color] = p(v) end
      for color, v in pairs(w.shadow) do c.shadow[color] = p(v) end
      table.insert(proto.connection_points, c)
    end
  end
end
