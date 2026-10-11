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
-- On les met dans la couche « object » (celle des arbres et des gros rochers), que le jeu trie par position ; et on
-- décale chaque image pour poser le pied du dessin (feet.lua) sur cette position : ce qui est plus bas à l'écran
-- passe devant. Les taches au sol restent dessous.
local feet = require("feet")
for _, name in pairs({ "green-hairy-grass", "green-carpet-grass", "green-small-grass", "brown-hairy-grass",
  "brown-carpet-grass", "green-asterisk", "green-asterisk-mini", "brown-asterisk", "brown-asterisk-mini",
  "red-asterisk", "green-pita", "green-pita-mini", "red-pita", "brown-fluff", "brown-fluff-dry", "green-bush-mini",
  "garballo", "garballo-mini-dry", "green-croton", "red-croton", "green-desert-bush", "red-desert-bush",
  "white-desert-bush", "small-rock", "tiny-rock", "medium-rock", "medium-sand-rock", "small-sand-rock",
  "muddy-stump" }) do
  local decorative = data.raw["optimized-decorative"][name]
  if decorative then
    decorative.render_layer = "object"
    for _, picture in pairs(decorative.pictures or {}) do
      local foot = feet[picture.filename]
      if foot and not picture.x and not picture.y then     -- image entière (pas un morceau de planche)
        local shift = picture.shift or { 0, 0 }
        picture.shift = { shift[1] or shift.x, -foot * (picture.scale or 1) / 32 }
      end
    end
  end
end

walk(data.raw)
