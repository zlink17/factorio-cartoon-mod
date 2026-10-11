-- Remplace les chemins de textures du jeu par leur version cartoon.
-- manifest.lua (généré par tools/build_manifest.py) liste les textures refaites,
-- stockées sous graphics/overrides/<mod>/ avec le même chemin que l'original.
-- Exemple : ["__base__/graphics/x.png"] = true

local MOD = "__factorio-cartoon-mod__"
local manifest = require("manifest")

local visited = {}

local function remap(path)
  if manifest[path] then
    -- "__base__/graphics/x.png" -> "__factorio-cartoon-mod__/graphics/overrides/base/x.png"
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
      -- toute chaîne listée : filename, icon, spritesheet, mais aussi les listes « filenames » (variantes),
      -- small_icon, mask_spritesheet...
      tbl[key] = remap(value)
    end
  end
end

-- Superpositions : les herbes, buissons et cailloux de Nauvis sont presque tous dans la couche « decorative », que le
-- jeu ne trie pas par profondeur ; avec des contours nets, une touffe posée derrière un caillou se voit par-dessus.
-- On les met dans la couche « lower-object », que le jeu trie par position ; et on décale chaque image pour poser le
-- pied du dessin (feet.lua) sur cette position : ce qui est plus bas à l'écran passe devant. Cette couche est sous
-- les entités (arbres, rochers, bâtiments) et sous leurs ombres. Pas « object » : les décorations y sont triées
-- entre elles seulement et dessinées après les entités, donc par-dessus les feuillages et les rochers. Les taches
-- au sol restent dans la couche « decorative », dessous.
local feet = require("feet")
local sorted = require("sorted_decoratives")
for _, name in pairs(sorted.decoratives) do
  local decorative = data.raw["optimized-decorative"][name]
  if decorative then
    decorative.render_layer = "lower-object"
    for _, picture in pairs(decorative.pictures or {}) do
      local foot = feet[picture.filename]
      if foot and not picture.x and not picture.y then     -- image entière (pas un morceau de planche)
        local shift = picture.shift or { 0, 0 }
        picture.shift = { shift[1] or shift.x, -foot * (picture.scale or 1) / 32 }
      end
    end
  end
end

-- Une décoration générée dans l'emprise d'un gros rocher sortirait de sous sa base. La couche « doodad » (celle des
-- décorations) ajoutée à son masque de collision empêche la génération de carte d'en poser là ; la migration
-- migrations/2026-10-11-decorations-sous-rochers.lua les retire des parties existantes.
for _, name in pairs(sorted.rocks) do
  local rock = data.raw["simple-entity"][name]
  if rock then
    local mask = rock.collision_mask or { layers = { item = true, meltable = true, object = true, player = true,
      water_tile = true, is_object = true, is_lower_object = true } }   -- masque par défaut des simple-entity
    mask.layers.doodad = true
    rock.collision_mask = mask
  end
end

walk(data.raw)
