-- Remplace les chemins de textures du jeu par leur version cartoon.
-- La liste des fichiers convertis est générée par tools/cartoonize.py
-- dans converted_paths.lua (table { ["__base__/graphics/..."] = true }).

local MOD = "__factorio-cartoon-mod__"
local converted = require("converted_paths")

local visited = {}

local function remap(path)
  if type(path) ~= "string" then return path end
  if converted[path] then
    -- "__base__/graphics/x.png" -> "__factorio-cartoon-mod__/graphics/base/x.png"
    local mod, rest = path:match("^__(.-)__/graphics/(.+)$")
    if mod and rest then
      return MOD .. "/graphics/" .. mod .. "/" .. rest
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
