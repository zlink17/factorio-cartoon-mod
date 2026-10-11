-- Scénario « vitrine » : construit des scènes de test sur une surface dédiée, en prend des captures, puis écrit
-- un fichier « fini.txt ». Lancé par tools/bench.py (qui ferme ensuite le jeu).
--
-- Captures : script-output/vitrine/<variante>/<scène>-<page>.png, <variante> = mod de textures actif ou « origine ».
-- Une page fait PAGE_W x PAGE_H cases, capturée à ZOOM (1 = 32 px par case, 2 = résolution des fichiers du jeu).
-- Scènes « detail-* » : vues rapprochées à la résolution du jeu, machines en marche. Captures animées :
-- <nom>-f00.png, -f01.png... prises tous les `step` ticks (tools/bench.py en fait des GIF).

local PAGE_W, PAGE_H = 64, 36
local ZOOM = 1
local SHOT_TICK = 180          -- laisse tourner machines et convoyeurs avant de capturer
local GROUND = "grass-1"

local variant = (script.active_mods["factorio-cartoon-mod"] and "cartoon")
  or (script.active_mods["factorio-pixel-mod"] and "pixel")
  or (script.active_mods["factorio-celshading-mod"] and "celshading") or "origine"
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

-- Capture animée d'une zone (cases) : `frames` images, une tous les `step` ticks.
local function animate(name, x, y, w, h, frames, step)
  shots[#shots + 1] = { name = name, position = { x + w / 2, y + h / 2 }, zoom = 2, w = w, h = h,
    frames = frames or 12, step = step or 2 }
end

-- Alimente une zone : interface d'énergie et sous-stations en haut et en bas (elles couvrent 9 cases autour d'elles).
local function power(x1, y1, x2, y2)
  local eei = create { name = "electric-energy-interface", position = { x1 + 1, y1 + 1 } }
  if eei then pcall(function() eei.power_production = 1e9; eei.electric_buffer_size = 1e10 end) end
  for x = x1 + 3, x2, 16 do
    create { name = "substation", position = { x + 1, y1 + 1 } }
    create { name = "substation", position = { x + 1, y2 - 1 } }
  end
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
-- Réglages de génération de Nauvis (avec Space Age, une surface créée sans réglages mélange toutes les planètes),
-- graine fixe, sans ennemis.
local function nauvis_settings(seed)
  local settings = game.surfaces.nauvis.map_gen_settings
  settings.seed = seed
  settings.peaceful_mode = true
  settings.autoplace_controls = settings.autoplace_controls or {}
  settings.autoplace_controls["enemy-base"] = { frequency = 0, size = 0, richness = 0 }
  return settings
end

local function world()
  local s = game.create_surface("monde", nauvis_settings(1234))
  s.always_day = true
  s.request_to_generate_chunks({ 0, 0 }, 4)
  s.force_generate_chunk_requests()
  local best, best_n = nil, -1      -- le gros rocher le plus entouré de décorations (vue « monde-rocher »)
  for _, e in pairs(s.find_entities_filtered { type = "simple-entity" }) do
    local around = #s.find_decoratives_filtered { position = e.position, radius = 4 }
    if around > best_n then best, best_n = e, around end
  end
  shots[#shots + 1] = { name = "monde-01", surface = s, position = { 0, 0 }, zoom = ZOOM, w = PAGE_W, h = PAGE_H }
  shots[#shots + 1] = { name = "monde-02", surface = s, position = { 40, 30 }, zoom = 2, w = PAGE_W / 2, h = PAGE_H / 2 }
  if best then
    shots[#shots + 1] = { name = "monde-rocher", surface = s, position = best.position, zoom = 2, w = 16, h = 9 }
  end
end

-- Vue rapprochée : bras robotisés au travail, dans les 4 directions, entre deux coffres.
local function detail_inserters()
  local names = { "burner-inserter", "inserter", "long-handed-inserter", "fast-inserter", "bulk-inserter" }
  local s = scene("detail-bras", 2, GROUND, 2)
  for i, name in ipairs(names) do
    local page, row = math.floor((i - 1) / 3), (i - 1) % 3
    local x0, y0 = page * (s.w + 8) + 2, s.y + 1 + row * 6
    for d, dir in ipairs(DIRECTIONS) do
      local cx, cy = x0 + (d - 1) * 7 + 2.5, y0 + 2.5
      create { name = "small-electric-pole", position = { cx - 2, cy - 2 } }
      local ins = create { name = name, position = { cx, cy }, direction = dir }
      if ins then
        if name == "burner-inserter" then ins.insert { name = "coal", count = 5 } end
        local p, q = ins.pickup_position, ins.drop_position
        local src = create { name = "iron-chest", position = { math.floor(p.x) + 0.5, math.floor(p.y) + 0.5 } }
        if src then src.insert { name = "iron-plate", count = 200 } end
        create { name = "wooden-chest", position = { math.floor(q.x) + 0.5, math.floor(q.y) + 0.5 } }
      end
    end
    local eei = create { name = "electric-energy-interface", position = { x0 - 1, y0 + 0.5 } }
    if eei then pcall(function() eei.power_production = 1e9; eei.electric_buffer_size = 1e10 end) end
    label(name, x0 + 14, y0 + 5.1, 1)
    animate("anim-bras-" .. name, x0 - 1, y0, 29, 6, 16, 3)
  end
end

-- Une ligne de `n` cases partant de (x, y) dans la direction `dir` : position du centre de la case k (0 = départ).
local VEC = { [defines.direction.north] = { 0, -1 }, [defines.direction.east] = { 1, 0 },
  [defines.direction.south] = { 0, 1 }, [defines.direction.west] = { -1, 0 } }
local function along(x, y, dir, k) local v = VEC[dir]; return { x + v[1] * k + 0.5, y + v[2] * k + 0.5 } end

local function load_belt(e, items)
  for line = 1, 2 do
    for k = 1, 3 do
      pcall(function() e.get_transport_line(line).insert_at_back({ name = items[(k + line) % #items + 1], count = 1 }) end)
    end
  end
end

local BELT_ITEMS = { "iron-ore", "copper-plate", "coal", "iron-gear-wheel", "stone", "electronic-circuit" }

-- Vue rapprochée : souterrains et répartiteurs de chaque niveau, dans les 4 directions, chargés d'objets.
local function detail_belts()
  local tiers = sorted(prototypes.entity, function(p) return p.type == "transport-belt" and not hidden(p) end)
  local su = scene("detail-souterrains", #tiers, GROUND, 2)
  local ss = scene("detail-repartiteurs", #tiers, GROUND, 2)
  local starts = {   -- départ (case) et direction de chaque ligne, dans une page de 32 x 18
    { 2, 3, defines.direction.east }, { 13, 7, defines.direction.west },
    { 17, 15, defines.direction.north }, { 25, 3, defines.direction.south },
  }
  for t, belt in ipairs(tiers) do
    local under = belt.name:gsub("transport%-belt", "underground-belt")
    local split = belt.name:gsub("transport%-belt", "splitter")
    -- souterrains : 3 convoyeurs, entrée, 2 cases enterrées, sortie, 3 convoyeurs
    local x0 = (t - 1) * (su.w + 8)
    for _, st in ipairs(starts) do
      local x, y, dir = x0 + st[1], su.y + st[2], st[3]
      for k = 0, 9 do
        local pos = along(x, y, dir, k)
        if k == 3 then create { name = under, position = pos, direction = dir, type = "input" }
        elseif k == 6 then create { name = under, position = pos, direction = dir, type = "output" }
        elseif k < 3 or k > 6 then
          local e = create { name = belt.name, position = pos, direction = dir }
          if e and k < 3 then load_belt(e, BELT_ITEMS) end
        end
      end
    end
    label(belt.name, x0 + 16, su.y + 16.5, 1)
    animate("anim-souterrain-" .. belt.name, x0 + 1, su.y + 1, 14, 8, 16, 2)
    -- répartiteurs : 3 convoyeurs sur 2 voies, le répartiteur, 3 convoyeurs
    for _, st in ipairs(starts) do
      local x, y, dir = x0 + st[1], ss.y + st[2], st[3]
      local v = VEC[dir]
      local side = { -v[2], v[1] }                   -- perpendiculaire : seconde voie
      if side[1] < 0 or side[2] < 0 then side = { -side[1], -side[2] } end
      for k = 0, 6 do
        local a, b = along(x, y, dir, k), along(x + side[1], y + side[2], dir, k)
        if k == 3 then
          create { name = split, position = { (a[1] + b[1]) / 2, (a[2] + b[2]) / 2 }, direction = dir }
        else
          for _, pos in ipairs({ a, b }) do
            local e = create { name = belt.name, position = pos, direction = dir }
            if e and k < 3 then load_belt(e, BELT_ITEMS) end
          end
        end
      end
    end
    label(belt.name, x0 + 16, ss.y + 16.5, 1)
    animate("anim-repartiteur-" .. belt.name, x0 + 1, ss.y + 1, 14, 10, 16, 2)
  end
end

-- Vue rapprochée : assembleurs au travail (coffre, bras, machine, bras, coffre).
local function detail_assemblers()
  local s = scene("detail-assembleurs", 1, GROUND, 2)
  power(0, s.y, s.w, s.y + s.h)
  for n = 1, 3 do
    local x = 4 + (n - 1) * 9
    local a = create { name = "assembling-machine-" .. n, position = { x + 0.5, s.y + 8.5 } }
    if a then a.set_recipe("iron-gear-wheel"); a.insert { name = "iron-plate", count = 200 } end
    local c = create { name = "iron-chest", position = { x + 0.5, s.y + 4.5 } }
    if c then c.insert { name = "iron-plate", count = 1000 } end
    create { name = "fast-inserter", position = { x + 0.5, s.y + 5.5 }, direction = defines.direction.south }
    create { name = "fast-inserter", position = { x + 0.5, s.y + 11.5 }, direction = defines.direction.south }
    create { name = "wooden-chest", position = { x + 0.5, s.y + 12.5 } }
    label("assembling-machine-" .. n, x + 0.5, s.y + 13.6, 1)
  end
  animate("anim-assembleurs", 1, s.y + 4, 28, 10, 16, 2)
end

-- Vue rapprochée : les minerais de Nauvis, chaque étape de richesse, puis un gisement.
local function detail_ores()
  local s = scene("detail-minerais", 1, GROUND, 2)
  for i, name in ipairs({ "iron-ore", "copper-ore", "coal", "stone", "uranium-ore" }) do
    local proto = prototypes.entity[name]
    local y = s.y + 1 + (i - 1) * 3.4
    local counts = get(proto, "stage_counts") or { 15000, 9500, 5500, 2900, 1300, 400, 150, 80 }
    for k = #counts, 1, -1 do                       -- du plus petit tas au plus gros
      create { name = name, position = { 1.5 + (#counts - k), y + 0.5 }, amount = counts[k], force = "neutral" }
    end
    for dx = 0, 17 do for dy = 0, 2 do
      create { name = name, position = { 11.5 + dx, y + dy + 0.5 }, amount = 2000 + (dx * 7 + dy * 13) % 9 * 2000,
        force = "neutral" }
    end end
    label(name, 5, y + 1.3, 0.8)
  end
end

-- Vue rapprochée : les objets intermédiaires sur les convoyeurs, un convoyeur par objet (3 colonnes de 10).
local LOT_ITEMS = { "iron-plate", "copper-plate", "steel-plate", "iron-gear-wheel", "copper-cable", "iron-stick",
  "electronic-circuit", "advanced-circuit", "processing-unit", "stone-brick", "wood", "plastic-bar", "sulfur",
  "battery", "engine-unit", "electric-engine-unit", "flying-robot-frame", "low-density-structure", "rocket-fuel",
  "solid-fuel", "explosives", "uranium-235", "uranium-238", "automation-science-pack", "logistic-science-pack",
  "military-science-pack", "chemical-science-pack", "production-science-pack", "utility-science-pack",
  "space-science-pack" }

local function detail_items()
  local s = scene("detail-objets", 1, GROUND, 2)
  for i, name in ipairs(LOT_ITEMS) do
    local col, row = math.floor((i - 1) / 10), (i - 1) % 10
    local x, y = 1 + col * 10.5, s.y + 0.5 + row * 1.7
    for k = 0, 5 do
      local e = create { name = "transport-belt", position = { x + k + 0.5, y + 0.5 }, direction = defines.direction.east }
      if e then load_belt(e, { name }) end
    end
    label(name, x + 8, y + 0.2, 0.45)
  end
end

-- Vue rapprochée : les décorations de Nauvis (plantes, cailloux, taches), plusieurs exemplaires de chaque.
local NAUVIS_DECORATIVES = { "green-hairy-grass", "green-carpet-grass", "green-small-grass", "brown-hairy-grass",
  "brown-carpet-grass", "green-asterisk", "green-asterisk-mini", "brown-asterisk", "brown-asterisk-mini",
  "red-asterisk", "green-pita", "green-pita-mini", "red-pita", "brown-fluff", "brown-fluff-dry", "green-bush-mini",
  "garballo", "garballo-mini-dry", "green-croton", "red-croton", "green-desert-bush", "red-desert-bush",
  "white-desert-bush", "small-rock", "tiny-rock", "medium-rock", "medium-sand-rock", "muddy-stump",
  "light-mud-decal", "dark-mud-decal", "cracked-mud-decal", "red-desert-decal", "sand-decal", "sand-dune-decal",
  "lichen-decal", "shroom-decal", "worms-decal" }

local function detail_decoratives()
  local s = scene("detail-decorations", 2, GROUND, 2)
  for i, name in ipairs(NAUVIS_DECORATIVES) do
    local page, k = math.floor((i - 1) / 24), (i - 1) % 24
    local x, y = page * (s.w + 8) + (k % 6) * 5.3, s.y + math.floor(k / 6) * 4.5
    if prototypes.decorative[name] then
      local list = {}
      for j, d in ipairs({ { 1, 1 }, { 3, 1.5 }, { 2, 2.6 } }) do
        list[j] = { name = name, position = { x + d[1], y + d[2] }, amount = 1 }
      end
      pcall(surface.create_decoratives, { check_collision = false, decoratives = list })
    end
    label(name, x + 2.6, y + 3.7, 0.4)
  end
end

-- Vue rapprochée : les arbres de Nauvis, quatre exemplaires de chaque (variantes et teintes tirées au hasard).
local function detail_trees()
  local names = {}
  for name, p in pairs(prototypes.entity) do
    if p.type == "tree" and (name:match("^tree%-") or name:match("dead") or name:match("dry")) then
      names[#names + 1] = name
    end
  end
  table.sort(names)
  local s = scene("detail-arbres", 3, GROUND, 2)
  for i, name in ipairs(names) do
    local page, k = math.floor((i - 1) / 8), (i - 1) % 8
    local x, y = page * (s.w + 8) + (k % 4) * 8, s.y + math.floor(k / 4) * 9
    for j = 0, 3 do
      create { name = name, position = { x + 1.5 + (j % 2) * 3.5, y + 3.5 + math.floor(j / 2) * 3.5 }, force = "neutral" }
    end
    label(name, x + 4, y + 8.3, 0.5)
  end
end

-- Vue rapprochée : superpositions. Un caillou par case, entouré d'herbes devant, derrière et sur les côtés : les
-- herbes de derrière doivent passer sous le caillou, celles de devant par-dessus.
local function detail_overlaps()
  local rocks = { "medium-rock", "small-rock", "tiny-rock", "medium-sand-rock" }
  local grasses = { "green-hairy-grass", "green-small-grass", "brown-hairy-grass", "green-croton", "green-pita",
    "green-bush-mini" }
  local s = scene("detail-superpositions", 1, GROUND, 2)
  for i, rock in ipairs(rocks) do
    for j, grass in ipairs(grasses) do
      local x, y = (j - 1) * 5.3 + 2.6, s.y + (i - 1) * 4.5 + 2
      local list = { { name = rock, position = { x, y }, amount = 1 } }   -- le caillou d'abord : le pire cas
      for k, d in ipairs({ { 0, -0.7 }, { -0.8, 0 }, { 0.8, 0 }, { 0, 0.7 }, { -0.5, 0.9 }, { 0.5, -0.9 } }) do
        list[k + 1] = { name = grass, position = { x + d[1], y + d[2] }, amount = 1 }
      end
      pcall(surface.create_decoratives, { check_collision = false, decoratives = list })
      label(rock .. " / " .. grass, x, y + 1.6, 0.3)
    end
  end
end

-- Vue rapprochée : gros rochers (cinq par ligne, variantes tirées au hasard, touffes autour ; grès sur du sable)
-- et un étang avec des poissons.
local function detail_rocks()
  local s = scene("detail-rochers", 1, GROUND, 2)
  local sand = {}
  for x = 0, 23 do for y = 12, 17 do sand[#sand + 1] = { name = "sand-1", position = { x, s.y + y } } end end
  local water = {}
  for x = 24, 31 do for y = 2, 15 do water[#water + 1] = { name = "water", position = { x, s.y + y } } end end
  surface.set_tiles(sand, true, false, true)
  surface.set_tiles(water, true, false, true)
  for i, name in ipairs({ "big-rock", "huge-rock", "big-sand-rock" }) do
    for j = 0, 4 do
      local x, y = j * 4.6 + 2.4, s.y + (i - 1) * 5.6 + 3
      create { name = name, position = { x, y }, force = "neutral" }
      local grass = i == 3 and "white-desert-bush" or "green-hairy-grass"
      pcall(surface.create_decoratives, { check_collision = false, decoratives = {
        { name = grass, position = { x - 1.6, y + 1.2 }, amount = 1 }, { name = grass, position = { x + 1.7, y - 0.6 }, amount = 1 } } })
    end
    label(name, 11, s.y + (i - 1) * 5.6 + 5.2, 0.5)
  end
  for k = 0, 5 do
    create { name = "fish", position = { 25.5 + (k % 2) * 3.5, s.y + 4 + math.floor(k / 2) * 3.5 } }
  end
end

-- Vue rapprochée : production de base. Fours en pierre (un éteint, deux allumés), au milieu de décorations.
local function detail_production()
  local s = scene("detail-production", 1, GROUND, 2)
  for k = 0, 2 do
    local x, y = 3 + k * 4, s.y + 4
    local f = create { name = "stone-furnace", position = { x, y } }
    if f and k > 0 then
      f.insert { name = "coal", count = 50 }
      f.insert { name = k == 1 and "iron-ore" or "copper-ore", count = 50 }
    end
  end
  label("stone-furnace", 7, s.y + 6.2, 0.6)
  animate("anim-fours", 1, s.y + 2, 12, 4, 16, 2)
  -- foreuses à charbon dans les 4 directions, sur du fer, avec du charbon
  for x = 0, 17 do
    for y = 8, 13 do
      create { name = "iron-ore", position = { x + 0.5, s.y + y + 0.5 }, amount = 5000 }
    end
  end
  local dirs = { "north", "east", "south", "west" }
  for k, d in ipairs(dirs) do
    local e = create { name = "burner-mining-drill", position = { 2 + (k - 1) * 4.5, s.y + 10 },
      direction = defines.direction[d] }
    if e then e.insert { name = "coal", count = 50 } end
    label(d, 2 + (k - 1) * 4.5, s.y + 12.3, 0.5)
  end
  animate("anim-foreuses-charbon", 0, s.y + 8, 18, 5, 16, 2)
  -- foreuses électriques dans les 4 directions, sur du cuivre, alimentées
  power(19, s.y, 32, s.y + 18)
  for x = 22, 31 do
    for y = 3, 14 do
      create { name = "copper-ore", position = { x + 0.5, s.y + y + 0.5 }, amount = 5000 }
    end
  end
  for k, d in ipairs({ "north", "east", "south", "west" }) do
    local x, y = 24.5 + ((k - 1) % 2) * 5, s.y + 5.5 + math.floor((k - 1) / 2) * 6
    create { name = "electric-mining-drill", position = { x, y }, direction = defines.direction[d] }
    label(d, x, y + 2.1, 0.5)
  end
  animate("anim-foreuses-electriques", 21, s.y + 3, 11, 12, 16, 2)
end

-- Vue rapprochée : stockage. Coffres en bois, fer et acier, seuls puis en rangées jointives, et en service
-- (coffre plein, bras, convoyeur, coffre de sortie).
local function detail_storage()
  local s = scene("detail-stockage", 1, GROUND, 2)
  local chests = { "wooden-chest", "iron-chest", "steel-chest" }
  for k, name in ipairs(chests) do
    local x = 3 + (k - 1) * 10
    create { name = name, position = { x + 0.5, s.y + 2.5 } }
    label(name, x + 0.5, s.y + 3.8, 0.5)
    for i = 0, 5 do create { name = name, position = { x + i + 0.5, s.y + 6.5 } } end
    for i = 0, 1 do for j = 0, 1 do create { name = name, position = { x + 7 + i + 0.5, s.y + 1.5 + j } } end end
  end
  power(0, s.y + 9, s.w, s.y + s.h)
  for k, name in ipairs(chests) do
    local x = 3 + (k - 1) * 10
    local c = create { name = name, position = { x + 0.5, s.y + 11.5 } }
    if c then c.insert { name = "iron-plate", count = 200 } end
    create { name = "fast-inserter", position = { x + 1.5, s.y + 11.5 }, direction = defines.direction.west }
    for i = 2, 5 do create { name = "transport-belt", position = { x + i + 0.5, s.y + 11.5 },
      direction = defines.direction.east } end
    create { name = "fast-inserter", position = { x + 6.5, s.y + 11.5 }, direction = defines.direction.west }
    create { name = chests[k % 3 + 1], position = { x + 7.5, s.y + 11.5 } }
  end
  animate("anim-stockage", 2, s.y + 9, 28, 5, 16, 2)
end

-- Vue rapprochée : énergie vapeur. Chaudières allumées dans les 4 directions : eau fournie et vapeur évacuée par
-- des tuyaux infinis, pour qu'elles brûlent en continu ; une chaudière éteinte (sans combustible) pour comparer.
local function detail_steam()
  local s = scene("detail-energie", 1, GROUND, 2)
  -- décalage (dx, dy) donné pour le nord, tourné vers la direction d (sens horaire, y vers le bas)
  local function turn(d, dx, dy)
    if d == "east" then return -dy, dx elseif d == "south" then return -dx, -dy
    elseif d == "west" then return dy, -dx end
    return dx, dy
  end
  local function infinity(x, y, fluid, mode)
    local p = create { name = "infinity-pipe", position = { x, y } }
    if p then pcall(function() p.set_infinity_pipe_filter { name = fluid, percentage = mode == "remove" and 0 or 1,
      mode = mode == "remove" and "exactly" or "at-least" } end) end
  end
  local spots = { { "north", 5.5, 4 }, { "east", 14, 4.5 }, { "south", 22.5, 4 }, { "west", 30, 4.5 } }
  for _, sp in ipairs(spots) do
    local d, cx, cy = sp[1], sp[2], s.y + sp[3]
    for row = 0, 1 do
      local y = cy + row * 7
      local b = create { name = "boiler", position = { cx, y }, direction = defines.direction[d] }
      if b and row == 0 then b.insert { name = "coal", count = 50 } end
      for _, side in ipairs({ -1, 1 }) do
        local dx, dy = turn(d, side * 2, 0.5)
        infinity(cx + dx, y + dy, "water", "add")
      end
      local dx, dy = turn(d, 0, -1.5)
      infinity(cx + dx, y + dy, "steam", "remove")
    end
    label(d, cx, cy + 2.6, 0.5)
  end
  animate("anim-chaudieres", 2, s.y + 1, 32, 7, 16, 2)
end

-- Vue rapprochée : machines à vapeur horizontale et verticale en charge (vapeur par tuyau infini, consommateur
-- électrique), et une à l'arrêt.
local function detail_steam_engines()
  local s = scene("detail-machines-vapeur", 1, GROUND, 2)
  local function steam_in(x, y)
    local p = create { name = "infinity-pipe", position = { x, y } }
    if p then pcall(function() p.set_infinity_pipe_filter { name = "steam", percentage = 1, temperature = 165,
      mode = "at-least" } end) end
  end
  local ey = s.y + 8.5
  create { name = "steam-engine", position = { 6.5, ey }, direction = defines.direction.east }
  steam_in(3.5, ey); steam_in(9.5, ey)
  create { name = "steam-engine", position = { 16.5, ey }, direction = defines.direction.north }
  steam_in(16.5, ey - 3); steam_in(16.5, ey + 3)
  create { name = "steam-engine", position = { 24.5, ey } , direction = defines.direction.east }   -- à l'arrêt
  create { name = "medium-electric-pole", position = { 11.5, ey - 2 } }
  create { name = "medium-electric-pole", position = { 13.5, ey + 1 } }
  local sink = create { name = "electric-energy-interface", position = { 12.5, ey + 3 } }
  if sink then pcall(function() sink.power_production = 0; sink.power_usage = 2e6; sink.electric_buffer_size = 1e6 end) end
  label("steam-engine", 12, ey + 4.5, 0.5)
  animate("anim-machines-vapeur", 2, ey - 3.5, 20, 7, 16, 2)
end

-- Vue rapprochée : pompes côtières dans les 4 directions autour d'un étang, eau évacuée par un tuyau infini
-- (elles tournent), et une à l'arrêt (sans sortie).
local function detail_offshore_pumps()
  local s = scene("detail-pompes-cotieres", 1, GROUND, 2)
  local x1, y1, x2, y2 = 8, s.y + 5, 18, s.y + 10
  local t = {}
  for x = x1, x2 - 1 do for y = y1, y2 - 1 do t[#t + 1] = { name = "water", position = { x, y } } end end
  surface.set_tiles(t, true, false, true)
  local function turn(d, dx, dy)
    if d == "east" then return -dy, dx elseif d == "south" then return -dx, -dy
    elseif d == "west" then return dy, -dx end
    return dx, dy
  end
  local shores = { north = { 11.5, y2 + 0.5 }, south = { 11.5, y1 - 0.5 }, east = { x1 - 0.5, y1 + 2.5 },
    west = { x2 + 0.5, y1 + 2.5 } }
  for _, d in ipairs({ "north", "east", "south", "west" }) do
    for _, k in ipairs({ 0, -0.5, 0.5, -1, 1 }) do
      local dx, dy = turn(d, 0, k)
      local pos = { shores[d][1] + dx, shores[d][2] + dy }
      if surface.can_place_entity { name = "offshore-pump", position = pos, direction = defines.direction[d],
        force = "player" } then
        local e = create { name = "offshore-pump", position = pos, direction = defines.direction[d] }
        if e then
          local ox, oy = turn(d, 0, 1)
          local p = create { name = "infinity-pipe", position = { e.position.x + ox, e.position.y + oy } }
          if p then pcall(function() p.set_infinity_pipe_filter { name = "water", percentage = 0, mode = "exactly" } end) end
        end
        break
      end
    end
  end
  local pos = { 15.5, y2 + 0.5 }          -- à l'arrêt : sans sortie
  for _, k in ipairs({ 0, 0.5, 1 }) do
    if surface.can_place_entity { name = "offshore-pump", position = { pos[1], pos[2] + k }, direction = defines.direction.north,
      force = "player" } then
      create { name = "offshore-pump", position = { pos[1], pos[2] + k }, direction = defines.direction.north }
      break
    end
  end
  label("offshore-pump", 13, y2 + 3.5, 0.5)
  animate("anim-pompes-cotieres", 4, s.y + 2, 18, 12, 16, 2)
end

-- Vue rapprochée : tuyaux. Un réseau (droits avec fenêtres, coudes, T, croix, bouts, tuyau isolé), des tuyaux
-- souterrains dans les 4 directions, et des assembleurs 2 et 3 à recette avec fluide (raccords et couvercles).
local function detail_pipes()
  local s = scene("detail-tuyaux", 1, GROUND, 2)
  local function pipe(x, y) create { name = "pipe", position = { x + 0.5, s.y + y + 0.5 } } end
  for x = 2, 11 do pipe(x, 2) end                     -- long droit horizontal (fenêtres)
  for y = 3, 9 do pipe(2, y) end                      -- long droit vertical, coudes aux coins
  for x = 3, 11 do pipe(x, 9) end
  for y = 3, 8 do pipe(11, y) end
  for x = 5, 8 do pipe(x, 5) end                      -- croix et T au milieu
  for y = 4, 7 do pipe(6, y) end
  pipe(9, 7)                                          -- tuyau isolé
  pipe(14, 3); pipe(14, 4)                            -- deux bouts
  pipe(16, 3); pipe(17, 3)
  local infinity = create { name = "infinity-pipe", position = { 12.5, s.y + 2.5 } }
  if infinity then pcall(function() infinity.set_infinity_pipe_filter { name = "water", percentage = 1 } end) end
  local ug = { { "north", 20, 2, 0, 1 }, { "south", 22, 6, 0, -1 }, { "east", 24, 2, -1, 0 }, { "west", 24, 7, 1, 0 } }
  for _, u in ipairs(ug) do
    local d, x, y, dx, dy = u[1], u[2], u[3], u[4], u[5]
    create { name = "pipe-to-ground", position = { x + 0.5, s.y + y + 0.5 }, direction = defines.direction[d] }
    pipe(x - dx, y - dy)
  end
  power(0, s.y + 10, s.w, s.y + s.h)
  local k = 0
  for _, tier in ipairs({ 2, 3 }) do
    for _, d in ipairs({ "north", "east" }) do
      local x, y = 3 + k * 7, s.y + 14.5
      local a = create { name = "assembling-machine-" .. tier, position = { x + 0.5, y }, direction = defines.direction[d] }
      if a then
        for _, r in ipairs({ "electric-engine-unit", "processing-unit" }) do
          pcall(function() a.force.recipes[r].enabled = true end)
          local ok, err = pcall(function() a.set_recipe(r) end)
          if ok and a.get_recipe() then break end
          note("recette " .. r .. " : " .. tostring(err))
        end
        if d == "east" then a.direction = defines.direction.east end   -- orientable seulement avec un fluide
        local dx, dy = 0, -2                          -- entrée de fluide : au nord, tournée avec la machine
        if d == "east" then dx, dy = 2, 0 end
        local p = create { name = "pipe", position = { x + 0.5 + dx, y + dy } }
        if p and k % 2 == 1 then p.destroy() end      -- une machine sur deux : raccord libre (couvercle)
      end
      label("assembling-machine-" .. tier .. " " .. d, x + 0.5, y + 2.4, 0.45)
      k = k + 1
    end
  end
  animate("anim-tuyaux", 1, s.y + 1, 26, 10, 4, 4)
end

-- Vue rapprochée : petits bâtiments. Laboratoires, radars (l'antenne tourne), petites lampes. (Les recherches
-- du banc étant toutes faites, les laboratoires ne travaillent pas : leur lueur se voit dans la galerie.)
local function detail_small_buildings()
  local s = scene("detail-petits-batiments", 1, GROUND, 2)
  power(0, s.y, s.w, s.y + s.h)
  for k = 0, 1 do
    local lab = create { name = "lab", position = { 5.5 + k * 5, s.y + 5.5 } }
    if lab and k == 0 then lab.insert { name = "automation-science-pack", count = 200 } end
  end
  create { name = "radar", position = { 18, s.y + 6 } }
  create { name = "radar", position = { 23, s.y + 6 } }
  for i = 0, 5 do create { name = "small-lamp", position = { 4.5 + i * 2, s.y + 10.5 } } end
  label("lab, radar, small-lamp", 14, s.y + 12, 0.5)
  animate("anim-petits-batiments", 2, s.y + 2, 24, 10, 16, 4)
end

-- Vue rapprochée : foreuses électriques « humides » (uranium, acide sulfurique) dans les 4 directions.
local function detail_wet_drills()
  local s = scene("detail-foreuses-humides", 1, GROUND, 2)
  power(0, s.y, s.w, s.y + s.h)
  for x = 2, 29 do
    for y = 3, 14 do
      create { name = "uranium-ore", position = { x + 0.5, s.y + y + 0.5 }, amount = 5000 }
    end
  end
  for k, d in ipairs({ "north", "east", "south", "west" }) do
    local x, y = 5.5 + (k - 1) * 7, s.y + 8.5
    local e = create { name = "electric-mining-drill", position = { x, y }, direction = defines.direction[d] }
    if e then pcall(function() e.insert_fluid { name = "sulfuric-acid", amount = 100 } end) end
    label(d, x, y + 2.2, 0.5)
  end
  animate("anim-foreuses-humides", 2, s.y + 6, 28, 6, 16, 2)
end

-- Vue rapprochée : mélange d'entités (arbres, gros rochers) et de décorations tout autour (devant, derrière, côtés) :
-- une décoration ne doit jamais passer sur un feuillage ou sur un rocher dont elle est derrière.
local function detail_mix()
  local s = scene("detail-melange", 1, GROUND, 2)
  local things = { "tree-01", "tree-05", "tree-08", "big-rock", "huge-rock", "tree-02" }
  for i, name in ipairs(things) do
    local x, y = (i - 1) * 5.3 + 2.6, s.y + 9
    create { name = name, position = { x, y }, force = "neutral" }
    local list = {}
    for k = 0, 15 do
      local a = k * math.pi / 8
      local d = 1.4 + (k % 2) * 0.8
      list[#list + 1] = { name = (k % 3 == 0) and "medium-rock" or "green-hairy-grass",
        position = { x + math.cos(a) * d, y + math.sin(a) * d * 0.9 }, amount = 1 }
    end
    pcall(surface.create_decoratives, { check_collision = false, decoratives = list })
    label(name, x, y + 3.2, 0.4)
  end
  -- convoyeurs posés sur des décorations : elles doivent rester dessous
  for i = 0, 29 do
    local x, y = i + 1.5, s.y + 14.5
    pcall(surface.create_decoratives, { check_collision = false, decoratives = {
      { name = (i % 4 == 0) and "medium-rock" or "green-hairy-grass", position = { x, y - 0.6 + (i % 3) * 0.6 }, amount = 1 } } })
    create { name = "transport-belt", position = { x, y }, direction = defines.direction.east, force = "player" }
  end
end

-- Vue rapprochée : les sols de Nauvis côte à côte (on y voit les transitions).
local function detail_grounds()
  local names = { "grass-1", "grass-2", "grass-3", "grass-4", "dry-dirt", "dirt-1", "dirt-2", "dirt-3", "dirt-4",
    "dirt-5", "dirt-6", "dirt-7", "sand-1", "sand-2", "sand-3", "red-desert-0", "red-desert-1", "red-desert-2",
    "red-desert-3", "water", "deepwater", "water-green", "water-shallow", "water-mud" }
  local s = scene("detail-sols", 2, GROUND, 2)
  for i, name in ipairs(names) do
    local page, k = math.floor((i - 1) / 12), (i - 1) % 12
    local x, y = page * (s.w + 8) + (k % 4) * 8, s.y + math.floor(k / 4) * 6
    local t = {}
    for dx = 0, 7 do for dy = 0, 5 do t[#t + 1] = { name = name, position = { x + dx, y + dy } } end end
    pcall(surface.set_tiles, t, true, false, true)
    label(name, x + 4, y + 2.7, 0.8)
  end
end

-- Vue rapprochée : eau et rives. Une rangée par sol (herbe, terre, sable, désert rouge), un lac de chaque eau.
local function detail_water()
  local grounds = { "grass-1", "dirt-4", "sand-1", "red-desert-1" }
  local waters = { "water", "deepwater", "water-green", "deepwater-green", "water-shallow", "water-mud" }
  local s = scene("detail-eau", 2, GROUND, 2)
  for gi, ground in ipairs(grounds) do
    local page, row = math.floor((gi - 1) / 2), (gi - 1) % 2
    local x0, y0 = page * (s.w + 8), s.y + row * 9
    local t = {}
    for x = x0, x0 + s.w - 1 do for y = y0, y0 + 8 do t[#t + 1] = { name = ground, position = { x, y } } end end
    surface.set_tiles(t, true, false, true)
    t = {}
    for wi, water in ipairs(waters) do
      local cx, cy = x0 + 2.8 + (wi - 1) * 5.3, y0 + 4.5
      for x = math.floor(cx - 3), math.ceil(cx + 3) do
        for y = y0 + 1, y0 + 7 do
          local a = math.atan2(y + 0.5 - cy, x + 0.5 - cx)
          local r = 2.3 + 0.6 * math.sin(3 * a + wi + gi) + 0.3 * math.cos(5 * a + gi)
          if (x + 0.5 - cx) ^ 2 + ((y + 0.5 - cy) * 0.9) ^ 2 < r * r then t[#t + 1] = { name = water, position = { x, y } } end
        end
      end
    end
    surface.set_tiles(t, true, false, true)
    if gi == 1 then
      for k = 0, 2 do create { name = "fish", position = { x0 + 2.8 + k * 5.3, y0 + 4.5 }, force = "neutral" } end
    end
    label(ground, x0 + s.w / 2, y0 + 7.9, 0.5)
  end
end

-- Vue rapprochée : falaises en chaînes fermées (anneaux sur la grille de 4 cases des falaises), parcourues dans les
-- deux sens : on voit les côtés, les coins intérieurs et extérieurs, et leurs raccords.
local function ring(x0, y0, n, clockwise)
  local cells = {}
  for k = 0, n - 1 do cells[#cells + 1] = { x0 + 4 * k, y0, "west", "east" } end
  for k = 1, n - 1 do cells[#cells + 1] = { x0 + 4 * (n - 1), y0 + 4 * k, "north", "south" } end
  for k = n - 2, 0, -1 do cells[#cells + 1] = { x0 + 4 * k, y0 + 4 * (n - 1), "east", "west" } end
  for k = n - 2, 1, -1 do cells[#cells + 1] = { x0, y0 + 4 * k, "south", "north" } end
  local m = #cells
  for i, c in ipairs(cells) do         -- entrée : d'où l'on vient ; sortie : où l'on va
    local prev, nxt = cells[(i - 2) % m + 1], cells[i % m + 1]
    local function side(from, to)
      if to[1] > from[1] then return "east" elseif to[1] < from[1] then return "west"
      elseif to[2] > from[2] then return "south" else return "north" end
    end
    local opposite = { east = "west", west = "east", north = "south", south = "north" }
    local entry, exit = opposite[side(prev, c)], side(c, nxt)
    if not clockwise then entry, exit = exit, entry end
    create { name = "cliff", position = { c[1], c[2] }, cliff_orientation = entry .. "-to-" .. exit, force = "neutral" }
  end
end

local function detail_cliffs()
  local s = scene("detail-falaises", 1, GROUND, 2)
  ring(4, s.y + 3, 3, true)
  ring(18, s.y + 3, 3, false)
  local t = {}                         -- un peu de sable et d'eau à côté : la falaise au milieu des sols
  for x = 0, 31 do for y = 15, 17 do t[#t + 1] = { name = "sand-1", position = { x, s.y + y } } end end
  surface.set_tiles(t, true, false, true)
end

local function build()
  surface = game.create_surface("vitrine", nauvis_settings(1))
  surface.always_day = true
  game.map_settings.enemy_expansion.enabled = false
  game.forces.enemy.set_cease_fire("player", true)
  game.forces.player.set_cease_fire("enemy", true)
  for _, step in ipairs({ buildings, belts, factory, resources, nature, tiles, items, world,
    detail_inserters, detail_belts, detail_assemblers, detail_production, detail_storage, detail_steam, detail_steam_engines, detail_offshore_pumps, detail_pipes, detail_small_buildings, detail_wet_drills, detail_ores, detail_items, detail_decoratives, detail_trees, detail_overlaps, detail_rocks, detail_mix, detail_grounds, detail_water, detail_cliffs }) do
    local ok, err = pcall(step)
    if not ok then note("ERREUR " .. tostring(err)) end
  end
end

script.on_init(function()
  build()
  helpers.write_file(OUT .. "journal.txt", table.concat(log_lines, "\n") .. "\n")
end)

local function shoot(shot, path)
  game.take_screenshot { surface = shot.surface or surface, position = shot.position, zoom = shot.zoom,
    resolution = { math.floor(shot.w * 32 * shot.zoom), math.floor(shot.h * 32 * shot.zoom) },
    path = OUT .. path .. ".png", daytime = 0, show_entity_info = false, force_render = true }
end

-- Captures fixes à SHOT_TICK ; captures animées à partir de SHOT_TICK, une image tous les `step` ticks ;
-- « fini.txt » une fois tout écrit.
script.on_event(defines.events.on_tick, function(event)
  local t = event.tick - SHOT_TICK
  if t < 0 then return end
  local pending = false
  for _, shot in ipairs(shots) do
    if not shot.frames then
      if t == 0 then shoot(shot, shot.name) end
    else
      local k = math.floor(t / shot.step)
      if t % shot.step == 0 and k < shot.frames then shoot(shot, string.format("%s-f%02d", shot.name, k)) end
      pending = pending or k < shot.frames
    end
  end
  if not pending then
    if not storage.done_at then
      game.set_wait_for_screenshots_to_finish()
      storage.done_at = event.tick
    elseif event.tick == storage.done_at + 10 then
      helpers.write_file(OUT .. "fini.txt", tostring(#shots) .. " captures\n")
    end
  end
end)
