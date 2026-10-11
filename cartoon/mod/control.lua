-- Gisements dégagés : avec le tri par profondeur (data-final-fixes.lua), herbes, buissons et cailloux sont dessinés
-- au-dessus des minerais et les cachent. On retire ces décorations des cases de minerai à la génération de chaque
-- morceau de carte. Les taches au sol (couche « decorative », sous les minerais) restent.
-- Une partie existante est traitée une fois à l'ajout ou à la mise à jour du mod ; /cartoon-minerais le refait.
local sorted = require("sorted_decoratives")

local function decorative_names()
  local names = {}
  for _, list in pairs({ sorted.grasses, sorted.singles }) do
    for _, name in pairs(list) do
      if prototypes.decorative[name] then names[#names + 1] = name end
    end
  end
  return names
end

-- Retire les décorations des cases de minerai de cette zone. Une rangée de cases de minerai contiguës = un seul appel.
local function clear_area(surface, area, names)
  local rows = {}
  for _, resource in pairs(surface.find_entities_filtered { area = area, type = "resource" }) do
    local x, y = math.floor(resource.position.x), math.floor(resource.position.y)
    local row = rows[y] or {}
    rows[y] = row
    row[#row + 1] = x
  end
  for y, xs in pairs(rows) do
    table.sort(xs)
    local i = 1
    while i <= #xs do
      local j = i
      while j < #xs and xs[j + 1] <= xs[j] + 1 do j = j + 1 end
      surface.destroy_decoratives { area = { { xs[i], y }, { xs[j] + 0.99, y + 0.99 } }, name = names }
      i = j + 1
    end
  end
end

local function clear_surface(surface, names)
  for chunk in surface.get_chunks() do
    if surface.is_chunk_generated(chunk) then clear_area(surface, chunk.area, names) end
  end
end

local function clear_all()
  local names = decorative_names()
  for _, surface in pairs(game.surfaces) do clear_surface(surface, names) end
end

script.on_event(defines.events.on_chunk_generated, function(event)
  clear_area(event.surface, event.area, decorative_names())
end)

script.on_init(clear_all)
script.on_configuration_changed(clear_all)

commands.add_command("cartoon-minerais", { "command-help.cartoon-minerais" }, function(event)
  local player = event.player_index and game.get_player(event.player_index)
  local surface = player and player.surface or game.surfaces.nauvis
  clear_surface(surface, decorative_names())
  game.print({ "cartoon-minerais.done", surface.name })
end)

-- Pour le sous-mod « terrain épuré », qui refait les décorations d'une surface et doit redégager les gisements.
remote.add_interface("factorio-cartoon-mod", {
  clear_ores = function(surface) clear_surface(surface, decorative_names()) end,
})
