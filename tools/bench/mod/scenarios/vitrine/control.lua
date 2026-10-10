-- Scénario « vitrine » : construit des scènes de test sur une surface dédiée, en prend des captures, puis écrit
-- un fichier « fini.txt ». Lancé par tools/bench.py (qui ferme ensuite le jeu).
--
-- Captures : script-output/vitrine/<variante>/<scène>-<page>.png, <variante> = mod de textures actif ou « origine ».
-- Une page fait PAGE_W x PAGE_H cases, capturée à ZOOM (1 = 32 px par case, 2 = résolution des fichiers du jeu).

local PAGE_W, PAGE_H = 64, 36
local ZOOM = 1
local SHOT_TICK = 180          -- laisse tourner machines et convoyeurs avant de capturer
local GROUND = "grass-1"

local variant = (script.active_mods["factorio-cartoon-mod"] and "cartoon")
  or (script.active_mods["factorio-pixel-mod"] and "pixel") or "origine"
local OUT = "vitrine/" .. variant .. "/"

local surface
local shots = {}               -- { name, position, zoom, w, h }
local next_y = 0               -- les scènes sont empilées vers le bas, une bande par scène
local log_lines = {}

local function note(msg) log_lines[#log_lines + 1] = msg end

local function get(obj, key)   -- lecture tolérante (un champ absent d'un LuaObject lève une erreur)
  local ok, v = pcall(function() return obj[key] end)
  if ok then return v end
end

local function hidden(proto) return get(proto, "hidden") == true end

local function sorted(dict, keep)
  local list = {}
  for _, p in pairs(dict) do
    if keep(p) then list[#list + 1] = p end
  end
  table.sort(list, function(a, b)
    if a.type ~= b.type then return a.type < b.type end
    return (get(a, "order") or "") .. a.name < (get(b, "order") or "") .. b.name
  end)
  return list
end

local function label(text, x, y, scale)
  rendering.draw_text { text = text, surface = surface, target = { x, y }, color = { 1, 1, 1 },
    scale = scale or 0.8, alignment = "center", vertical_alignment = "top" }
end

local function create(params)
  params.force = params.force or "player"
  local ok, entity = pcall(surface.create_entity, params)
  if not ok or not entity then
    note("échec : " .. params.name .. (ok and "" or (" : " .. tostring(entity))))
    return nil
  end
  return entity
end

-- Prépare une zone : chunks générés, tout retiré, sol uni.
local function clear(x1, y1, x2, y2, ground)
  surface.request_to_generate_chunks({ (x1 + x2) / 2, (y1 + y2) / 2 },
    math.ceil(math.max(x2 - x1, y2 - y1) / 64) + 1)
  surface.force_generate_chunk_requests()
  local area = { { x1, y1 }, { x2, y2 } }
  for _, e in pairs(surface.find_entities_filtered { area = area }) do
    if e.valid and e.type ~= "character" then e.destroy() end
  end
  surface.destroy_decoratives { area = area }
  local tiles = {}
  for x = x1, x2 - 1 do
    for y = y1, y2 - 1 do tiles[#tiles + 1] = { name = ground or GROUND, position = { x, y } } end
  end
  surface.set_tiles(tiles, true, true, true)
end

-- Ouvre une scène : nouvelle bande, pages côte à côte vers la droite.
local function scene(name, pages, ground, zoom)
  local s = { name = name, y = next_y, pages = pages, zoom = zoom or ZOOM }
  local w, h = PAGE_W / (s.zoom / ZOOM), PAGE_H / (s.zoom / ZOOM)
  s.w, s.h = w, h
  for p = 0, pages - 1 do
    local x = p * (w + 8)
    clear(x - 4, s.y - 4, x + w + 4, s.y + h + 4, ground)   -- marge : rien ne déborde sur les bords
    shots[#shots + 1] = { name = string.format("%s-%02d", name, p + 1), position = { x + w / 2, s.y + h / 2 },
      zoom = s.zoom, w = w, h = h }
  end
  next_y = next_y + h + 8
  return s
end

-- Range des cases (largeur, hauteur) en lignes, page par page ; place(item, x, y) les construit.
local function pack(name, items, size_of, place, ground, zoom)
  local layout, page, x, y, row_h = {}, 0, 1, 1, 0
  local probe = { zoom = zoom or ZOOM }
  local w, h = PAGE_W / (probe.zoom / ZOOM), PAGE_H / (probe.zoom / ZOOM)
  for _, item in ipairs(items) do
    local cw, ch = size_of(item)
    if x + cw > w - 1 then x, y, row_h = 1, y + row_h, 0 end
    if y + ch > h - 1 then page, x, y, row_h = page + 1, 1, 1, 0 end
    layout[#layout + 1] = { item = item, page = page, x = x, y = y }
    x, row_h = x + cw, math.max(row_h, ch)
  end
  local s = scene(name, page + 1, ground, zoom)
  for _, l in ipairs(layout) do place(l.item, l.page * (s.w + 8) + l.x, s.y + l.y) end
end

local function box_size(proto)
  local box = get(proto, "collision_box") or { left_top = { x = 0, y = 0 }, right_bottom = { x = 1, y = 1 } }
  local w = math.max(1, math.ceil(box.right_bottom.x - box.left_top.x))
  local h = math.max(1, math.ceil(box.right_bottom.y - box.left_top.y))
  return w, h
end

local DIRECTIONS = { defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west }
local SKIP_BUILDING = {
  ["straight-rail"] = true, ["curved-rail-a"] = true, ["curved-rail-b"] = true, ["half-diagonal-rail"] = true,
  ["legacy-straight-rail"] = true, ["legacy-curved-rail"] = true, ["rail-ramp"] = true, ["elevated-straight-rail"] = true,
  ["elevated-curved-rail-a"] = true, ["elevated-curved-rail-b"] = true, ["elevated-half-diagonal-rail"] = true,
  ["rail-support"] = true, ["locomotive"] = true, ["cargo-wagon"] = true, ["fluid-wagon"] = true,
  ["artillery-wagon"] = true, ["infinity-cargo-wagon"] = true,
}

-- Catalogue : chaque bâtiment constructible, dans les 4 directions s'il en a.
local function buildings()
  local list = sorted(prototypes.entity, function(p)
    local flags = get(p, "flags") or {}
    local items = get(p, "items_to_place_this")
    return flags["player-creation"] and items and #items > 0 and not hidden(p) and not SKIP_BUILDING[p.type]
  end)
  pack("batiments", list, function(p)
    local w, h = box_size(p)
    local n = get(p, "supports_direction") and 4 or 1
    local side = math.max(w, h)
    return n * (side + 1) + 1, side + 3
  end, function(p, x, y)
    local side = math.max(box_size(p))
    local dirs = get(p, "supports_direction") and DIRECTIONS or { defines.direction.north }
    for i, dir in ipairs(dirs) do
      local cx = x + (i - 1) * (side + 1) + side / 2
      local params = { name = p.name, position = { cx, y + side / 2 }, direction = dir }
      if p.type == "underground-belt" then params.type = (i % 2 == 1) and "input" or "output" end
      create(params)
    end
    label(p.name, x + #dirs * (side + 1) / 2, y + side + 0.3, 0.7)
  end)
end

-- Convoyeurs : une boucle chargée par niveau, souterrain, répartiteur et bout de ligne.
local function belts()
  local tiers = sorted(prototypes.entity, function(p) return p.type == "transport-belt" and not hidden(p) end)
  local s = scene("convoyeurs", 1, GROUND, 2)
  local items = { "iron-ore", "copper-ore", "coal", "stone", "iron-plate", "copper-plate", "iron-gear-wheel",
    "electronic-circuit" }
  for t, belt in ipairs(tiers) do
    local ox, oy = 2 + (t - 1) * 8, s.y + 2
    local L, H = 5, 4
    local loop = {}
    for x = 0, L - 1 do loop[#loop + 1] = { x, 0, defines.direction.east } end
    for y = 0, H - 1 do loop[#loop + 1] = { L, y, defines.direction.south } end
    for x = L, 1, -1 do loop[#loop + 1] = { x, H, defines.direction.west } end
    for y = H, 1, -1 do loop[#loop + 1] = { 0, y, defines.direction.north } end
    for i, b in ipairs(loop) do
      local e = create { name = belt.name, position = { ox + b[1] + 0.5, oy + b[2] + 0.5 }, direction = b[3] }
      if e then
        for line = 1, 2 do
          pcall(function() e.get_transport_line(line).insert_at_back({ name = items[(i + line) % #items + 1], count = 1 }) end)
        end
      end
    end
    local under = belt.name:gsub("transport%-belt", "underground-belt")
    local split = belt.name:gsub("transport%-belt", "splitter")
    local y2 = oy + H + 3
    create { name = belt.name, position = { ox + 0.5, y2 + 0.5 }, direction = defines.direction.east }
    create { name = under, position = { ox + 1.5, y2 + 0.5 }, direction = defines.direction.east, type = "input" }
    create { name = under, position = { ox + 4.5, y2 + 0.5 }, direction = defines.direction.east, type = "output" }
    create { name = belt.name, position = { ox + 5.5, y2 + 0.5 }, direction = defines.direction.east }
    create { name = split, position = { ox + 2.5, y2 + 4 }, direction = defines.direction.north }
    create { name = belt.name, position = { ox + 2.5, y2 + 5.5 }, direction = defines.direction.north }
    create { name = belt.name, position = { ox + 3.5, y2 + 5.5 }, direction = defines.direction.north }
    label(belt.name, ox + 3, oy + H + 1.2, 1)
  end
end

-- Usine alimentée : assembleurs au travail, bras, fours, foreuses, poteaux reliés.
local function factory()
  local s = scene("usine", 1, GROUND)
  local y0 = s.y
  local eei = create { name = "electric-energy-interface", position = { 2, y0 + 3 } }
  if eei then pcall(function() eei.power_production = 1e9; eei.electric_buffer_size = 1e10 end) end
  for i = 0, 3 do create { name = "substation", position = { 6 + i * 16, y0 + 9 } } end
  for i = 0, 3 do create { name = "substation", position = { 6 + i * 16, y0 + 25 } } end
  -- assembleurs avec coffre -> bras -> machine -> bras -> coffre
  local inserters = { "burner-inserter", "inserter", "long-handed-inserter", "fast-inserter", "bulk-inserter" }
  for n = 1, 3 do
    local x = 10 + (n - 1) * 8
    local a = create { name = "assembling-machine-" .. n, position = { x + 0.5, y0 + 6.5 } }
    if a then
      a.set_recipe("iron-gear-wheel")
      a.insert { name = "iron-plate", count = 100 }
    end
    local chest = create { name = "iron-chest", position = { x + 0.5, y0 + 2.5 } }
    if chest then chest.insert { name = "iron-plate", count = 1000 } end
    create { name = inserters[n + 1], position = { x + 0.5, y0 + 3.5 + (n == 2 and 0 or 1) }, direction = defines.direction.north }
    create { name = "inserter", position = { x + 0.5, y0 + 8.5 }, direction = defines.direction.north }
    create { name = "wooden-chest", position = { x + 0.5, y0 + 9.5 } }
  end
  -- fours et foreuses sur minerai
  local function ore(name, x1, y1, x2, y2)
    for x = x1, x2 do for y = y1, y2 do
      create { name = name, position = { x + 0.5, y + 0.5 }, amount = 5000, force = "neutral" }
    end end
  end
  ore("iron-ore", 36, y0 + 2, 47, y0 + 10)
  ore("coal", 50, y0 + 2, 55, y0 + 10)
  local d = create { name = "electric-mining-drill", position = { 38.5, y0 + 4.5 }, direction = defines.direction.south }
  create { name = "electric-mining-drill", position = { 42.5, y0 + 4.5 }, direction = defines.direction.east }
  local b = create { name = "burner-mining-drill", position = { 52, y0 + 4 }, direction = defines.direction.south }
  if b then b.insert { name = "coal", count = 50 } end
  for i, f in ipairs({ "stone-furnace", "steel-furnace", "electric-furnace" }) do
    local e = create { name = f, position = { 10 + (i - 1) * 6 + 0.5, y0 + 16.5 } }
    if e then e.insert { name = "iron-ore", count = 50 }; pcall(function() e.insert { name = "coal", count = 50 } end) end
  end
  -- énergie vapeur et lignes de poteaux
  create { name = "boiler", position = { 34.5, y0 + 17 }, direction = defines.direction.north }
  create { name = "steam-engine", position = { 34.5, y0 + 21.5 }, direction = defines.direction.north }
  for i, pole in ipairs({ "small-electric-pole", "medium-electric-pole", "big-electric-pole" }) do
    for k = 0, 3 do create { name = pole, position = { 40 + k * (4 + i * 3), y0 + 18 + i * 5 } } end
  end
  create { name = "lab", position = { 22.5, y0 + 24.5 } }
  create { name = "radar", position = { 28, y0 + 25 } }
  create { name = "small-lamp", position = { 16.5, y0 + 24.5 } }
end

-- Minerais : pour chaque ressource, une rangée de quantités croissantes (toutes les étapes) et un gisement.
local function resources()
  local list = sorted(prototypes.entity, function(p) return p.type == "resource" and not hidden(p) end)
  pack("minerais", list, function() return 20, 6 end, function(p, x, y)
    local stages = { 10, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000 }
    for i, amount in ipairs(stages) do
      create { name = p.name, position = { x + i - 0.5, y + 0.5 }, amount = amount, force = "neutral" }
    end
    for dx = 11, 17 do for dy = 0, 3 do
      create { name = p.name, position = { x + dx + 0.5, y + dy + 0.5 }, amount = 5000 + (dx * 7 + dy * 13) % 9 * 2000,
        force = "neutral" }
    end end
    label(p.name, x + 9, y + 4.3, 0.8)
  end)
end

-- Nature : arbres, rochers et autres entités simples, poissons, plantes ; falaises ; décorations.
local function nature()
  local list = sorted(prototypes.entity, function(p)
    return (p.type == "tree" or p.type == "simple-entity" or p.type == "fish" or p.type == "plant") and not hidden(p)
  end)
  pack("nature", list, function(p) local w, h = box_size(p); return math.max(w, 4) + 1, math.max(h, 3) + 2 end,
    function(p, x, y)
      local w = math.max(box_size(p), 4)
      create { name = p.name, position = { x + w / 2, y + 1.5 }, force = "neutral" }
      label(p.name, x + w / 2, y + 3, 0.5)
    end)
  local cliffs = sorted(prototypes.entity, function(p) return p.type == "cliff" end)
  local orientations = { "west-to-east", "north-to-south", "east-to-west", "south-to-north", "west-to-north",
    "north-to-east", "east-to-south", "south-to-west" }
  pack("falaises", cliffs, function() return PAGE_W - 2, 9 end, function(p, x, y)
    for i, o in ipairs(orientations) do
      create { name = p.name, position = { x + 4 + (i - 1) * 7, y + 4 }, cliff_orientation = o, force = "neutral" }
    end
    label(p.name, x + 30, y + 7.5, 0.8)
  end)
  local decos = sorted(prototypes.decorative, function(p) return not hidden(p) end)
  pack("decorations", decos, function() return 4, 3 end, function(p, x, y)
    pcall(surface.create_decoratives, { check_collision = false,
      decoratives = { { name = p.name, position = { x + 1, y }, amount = 1 }, { name = p.name, position = { x + 2, y + 1 }, amount = 1 } } })
    label(p.name, x + 2, y + 1.8, 0.35)
  end)
end

-- Sols : un carré de chaque sol, sur fond d'herbe (on voit ainsi les transitions).
local function tiles()
  local list = sorted(prototypes.tile, function(p) return not hidden(p) and p.name ~= "out-of-map" end)
  pack("sols", list, function() return 8, 7 end, function(p, x, y)
    local t = {}
    for dx = 1, 6 do for dy = 0, 4 do t[#t + 1] = { name = p.name, position = { x + dx, y + dy } } end end
    pcall(surface.set_tiles, t, true, false, true)
    label(p.name, x + 4, y + 5.2, 0.6)
  end)
end

-- Objets : chaque objet posé au sol (même image que sur les convoyeurs).
local function items()
  local list = sorted(prototypes.item, function(p) return not hidden(p) and not get(p, "parameter") end)
  pack("objets", list, function() return 4, 3 end, function(p, x, y)
    create { name = "item-on-ground", position = { x + 2, y + 1 }, stack = { name = p.name, count = 1 }, force = "neutral" }
    label(p.name, x + 2, y + 1.6, 0.35)
  end)
end

-- Monde généré : une portion de carte avec sa nature, ses minerais, son eau (graine fixe).
local function world()
  local s = game.create_surface("monde", { seed = 1234, peaceful_mode = true,
    autoplace_controls = { ["enemy-base"] = { frequency = 0, size = 0, richness = 0 } } })
  s.always_day = true
  s.request_to_generate_chunks({ 0, 0 }, 4)
  s.force_generate_chunk_requests()
  shots[#shots + 1] = { name = "monde-01", surface = s, position = { 0, 0 }, zoom = ZOOM, w = PAGE_W, h = PAGE_H }
  shots[#shots + 1] = { name = "monde-02", surface = s, position = { 40, 30 }, zoom = 2, w = PAGE_W / 2, h = PAGE_H / 2 }
end

local function build()
  surface = game.create_surface("vitrine", { seed = 1, peaceful_mode = true,
    autoplace_controls = { ["enemy-base"] = { frequency = 0, size = 0, richness = 0 } } })
  surface.always_day = true
  game.map_settings.enemy_expansion.enabled = false
  game.forces.enemy.set_cease_fire("player", true)
  game.forces.player.set_cease_fire("enemy", true)
  for _, step in ipairs({ buildings, belts, factory, resources, nature, tiles, items, world }) do
    local ok, err = pcall(step)
    if not ok then note("ERREUR " .. tostring(err)) end
  end
end

script.on_init(function()
  build()
  helpers.write_file(OUT .. "journal.txt", table.concat(log_lines, "\n") .. "\n")
end)

script.on_nth_tick(SHOT_TICK, function(event)
  if event.tick == SHOT_TICK then
    for _, shot in ipairs(shots) do
      game.take_screenshot { surface = shot.surface or surface, position = shot.position, zoom = shot.zoom,
        resolution = { math.floor(shot.w * 32 * shot.zoom), math.floor(shot.h * 32 * shot.zoom) },
        path = OUT .. shot.name .. ".png", daytime = 0, show_entity_info = false, force_render = true }
    end
    game.set_wait_for_screenshots_to_finish()
  elseif event.tick == 2 * SHOT_TICK then
    helpers.write_file(OUT .. "fini.txt", tostring(#shots) .. " captures\n")
  end
end)
