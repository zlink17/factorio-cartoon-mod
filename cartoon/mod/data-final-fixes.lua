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
-- On les met dans des couches que le jeu trie par position (sorted_decoratives.lua : herbes dans « remnants », le
-- reste dans « floor », au-dessus) ; et on décale chaque image pour poser le pied du dessin (feet.lua) sur cette
-- position : ce qui est plus bas à l'écran passe devant. Ces couches sont sous les convoyeurs, les objets au sol et
-- les entités (arbres, rochers, bâtiments), et sous leurs ombres. Pas « object » : les décorations y sont triées
-- entre elles seulement et dessinées après les entités, par-dessus les feuillages et les rochers ; ni
-- « lower-object » : au-dessus des convoyeurs. Le générateur de carte pose des décorations sous les gros rochers,
-- comme à l'origine : elles y sont cachées par le rocher. Les taches au sol restent dans « decorative », dessous.
local feet = require("feet")
local sorted = require("sorted_decoratives")
for layer, names in pairs({ remnants = sorted.grasses, floor = sorted.singles }) do
  for _, name in pairs(names) do
    local decorative = data.raw["optimized-decorative"][name]
    if decorative then
      decorative.render_layer = layer
      for _, picture in pairs(decorative.pictures or {}) do
        local foot = feet[picture.filename]
        if foot and not picture.x and not picture.y then     -- image entière (pas un morceau de planche)
          local shift = picture.shift or { 0, 0 }
          picture.shift = { shift[1] or shift.x, -foot * (picture.scale or 1) / 32 }
        end
      end
    end
  end
end

walk(data.raw)
