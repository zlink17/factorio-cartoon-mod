-- Scénario « galerie » : une carte de Nauvis où une clairière regroupe, zone par zone, tout ce que le mod cartoon
-- a redessiné, machines en marche (alimentées et réapprovisionnées sans fin). Hors de la clairière : la carte
-- générée normalement (sols, arbres, rochers, décorations, minerais), sans ennemis.
--
-- Fenêtre « Galerie » en haut à gauche : aller à une zone, jour permanent ou cycle jour/nuit, mode éditeur.
-- Mode triche actif et recherches faites : tout est constructible pour essayer à la main.
--
-- Ajouter un lot : écrire sa fonction de construction et l'ajouter à ZONES (taille en cases, titre). Les zones sont
-- rangées automatiquement en lignes. Les coordonnées passées à build(x, y) sont le coin haut gauche de la zone.
--
-- Avec le mod du banc d'essai (cartoon-bench, lancé par tools/galerie.py), le scénario capture chaque zone dans
-- script-output/galerie/<variante>/ puis écrit fini.txt.

local GROUND = "grass-1"
local ROW_WIDTH = 130          -- largeur maximale d'une ligne de zones (cases)
local GAP_X, GAP_Y = 10, 12    -- espaces entre zones (la place des titres au-dessus)
local REFILL_TICKS = 120       -- réapprovisionnement des machines

local BENCH = script.active_mods["cartoon-bench"] ~= nil
local CARTOON = script.active_mods["factorio-cartoon-mod"] ~= nil
local VARIANT = CARTOON and "cartoon" or "origine"

local N, E, S, W = defines.direction.north, defines.direction.east, defines.direction.south, defines.direction.west
local DIRS = { { "nord", N }, { "est", E }, { "sud", S }, { "ouest", W } }

local surface
local log_lines = {}
local function note(msg) log_lines[#log_lines + 1] = msg end

local function get(obj, key)   -- lecture tolérante (un champ absent d'un LuaObject lève une erreur)
  local ok, v = pcall(function() return obj[key] end)
  if ok then return v end
end

local function label(text, x, y, scale, align)
  rendering.draw_text { text = text, surface = surface, target = { x, y }, color = { 1, 1, 1 },
    scale = (scale or 0.8) * 1.6, alignment = align or "center", vertical_alignment = "top" }
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

local function tiles(name, x1, y1, x2, y2)      -- rectangle [x1, x2[ x [y1, y2[
  local t = {}
  for x = x1, x2 - 1 do for y = y1, y2 - 1 do t[#t + 1] = { name = name, position = { x, y } } end end
  pcall(surface.set_tiles, t, true, false, true)
end

local function ore(name, x1, y1, x2, y2)       -- gisement riche, rectangle de cases [x1, x2[ x [y1, y2[
  for x = x1, x2 - 1 do
    for y = y1, y2 - 1 do
      create { name = name, position = { x + 0.5, y + 0.5 }, force = "neutral",
        amount = 200000 + ((x * 7 + y * 13) % 9) * 20000 }
    end
  end
end

local function decoratives(list)
  pcall(surface.create_decoratives, { check_collision = false, decoratives = list })
end

-- Machines entretenues : combustible, entrées et sorties remis à niveau toutes les REFILL_TICKS.
-- spec : { fuel = true, input = { nom, nombre }, clear = true, fluid = { nom, quantité } }
local function keep(entity, spec)
  if not entity then return end
  spec.entity = entity
  storage.keep[#storage.keep + 1] = spec
end

local function refill()
  for _, k in ipairs(storage.keep) do
    local e = k.entity
    if e.valid then
      if k.fuel then
        local inv = e.get_fuel_inventory()
        if inv and inv.get_item_count("coal") < 10 then inv.insert { name = "coal", count = 20 } end
      end
      if k.input and e.get_item_count(k.input[1]) < k.input[2] / 2 then
        e.insert { name = k.input[1], count = k.input[2] }
      end
      if k.clear then
        local inv = e.type == "container" and e.get_inventory(defines.inventory.chest) or e.get_output_inventory()
        if inv then inv.clear() end
      end
      if k.fluid and e.get_fluid_count(k.fluid[1]) < k.fluid[2] / 2 then
        pcall(e.insert_fluid, { name = k.fluid[1], amount = k.fluid[2] })
      end
    end
  end
end

-- Interface d'énergie (production illimitée) et sous-stations aux positions données, reliées entre elles.
local function power(eei_pos, substations)
  local eei = create { name = "electric-energy-interface", position = eei_pos }
  if eei then pcall(function() eei.power_production = 1e9; eei.electric_buffer_size = 1e10 end) end
  for _, pos in ipairs(substations) do create { name = "substation", position = pos } end
end

-- Coffre posé là où une machine dépose (foreuse) ou prend (bras) ses objets.
local function chest_at(name, pos)
  return create { name = name, position = { math.floor(pos.x) + 0.5, math.floor(pos.y) + 0.5 } }
end

------------------------------------------------------------------------------------------------------------------------
-- Convoyeurs en boucle fermée : les objets tournent sans fin.

local function dir_to(dx, dy)
  if dx > 0 then return E elseif dx < 0 then return W elseif dy > 0 then return S end
  return N
end

-- Cases du tour d'un rectangle w x h, sens horaire depuis le coin haut gauche (ou antihoraire).
local function perimeter(w, h, ccw)
  local cells = {}
  for x = 0, w - 1 do cells[#cells + 1] = { x, 0 } end
  for y = 1, h - 1 do cells[#cells + 1] = { w - 1, y } end
  for x = w - 2, 0, -1 do cells[#cells + 1] = { x, h - 1 } end
  for y = h - 2, 1, -1 do cells[#cells + 1] = { 0, y } end
  if ccw then
    local r = {}
    for i = #cells, 1, -1 do r[#r + 1] = cells[i] end
    cells = r
  end
  return cells
end

local function load_belt(e, items, k)
  for line = 1, 2 do
    pcall(function() e.get_transport_line(line).insert_at_back { name = items[(k + line) % #items + 1], count = 1 } end)
  end
end

-- Boucle de convoyeurs ; specials[{x, y}] (clé "x,y") : "in"/"out" (souterrain), "skip" (case enterrée),
-- "split" (répartiteur, sa seconde sortie part vers l'extérieur sur deux cases).
local function belt_loop(belt, x0, y0, w, h, ccw, specials, items)
  local cells = perimeter(w, h, ccw)
  local under = belt:gsub("transport%-belt", "underground-belt")
  local split = belt:gsub("transport%-belt", "splitter")
  for i, c in ipairs(cells) do
    local nx = cells[i % #cells + 1]
    local dir = dir_to(nx[1] - c[1], nx[2] - c[2])
    local pos = { x0 + c[1] + 0.5, y0 + c[2] + 0.5 }
    local kind = specials and specials[c[1] .. "," .. c[2]]
    if kind == "in" or kind == "out" then
      create { name = under, position = pos, direction = dir, type = kind == "in" and "input" or "output" }
    elseif kind == "split" then
      local ox, oy = 0, 0                          -- vers l'extérieur du rectangle
      if c[2] == 0 then oy = -1 elseif c[2] == h - 1 then oy = 1 elseif c[1] == 0 then ox = -1 else ox = 1 end
      create { name = split, position = { pos[1] + ox / 2, pos[2] + oy / 2 }, direction = dir }
      local vx, vy = nx[1] - c[1], nx[2] - c[2]
      for k = 1, 2 do
        create { name = belt, position = { pos[1] + ox + vx * k, pos[2] + oy + vy * k }, direction = dir }
      end
    elseif kind ~= "skip" then
      local e = create { name = belt, position = pos, direction = dir }
      if e and items and i % 2 == 1 then load_belt(e, items, i) end
    end
  end
end

local BELT_ITEMS = { "iron-ore", "copper-plate", "coal", "iron-gear-wheel", "stone", "electronic-circuit" }

local function belt_tiers()
  local list = {}
  for name, p in pairs(prototypes.entity) do
    if p.type == "transport-belt" and not get(p, "hidden") then list[#list + 1] = p end
  end
  table.sort(list, function(a, b) return a.order .. a.name < b.order .. b.name end)
  return list
end

-- Étape 1 : convoyeurs, souterrains, répartiteurs de chaque niveau.
local function build_belts(x0, y0)
  for t, p in ipairs(belt_tiers()) do
    local x = x0 + (t - 1) * 16 + 1
    -- boucle horaire avec un souterrain en haut (vers l'est) et un en bas (vers l'ouest)
    belt_loop(p.name, x, y0 + 1, 12, 6, false,
      { ["3,0"] = "in", ["4,0"] = "skip", ["5,0"] = "skip", ["6,0"] = "out",
        ["8,5"] = "in", ["7,5"] = "skip", ["6,5"] = "skip", ["5,5"] = "out" }, BELT_ITEMS)
    -- boucle antihoraire avec un répartiteur en haut et un en bas
    belt_loop(p.name, x, y0 + 11, 12, 6, true, { ["5,0"] = "split", ["6,5"] = "split" }, BELT_ITEMS)
    label(p.name, x + 6, y0 + 19, 0.8)
  end
end

------------------------------------------------------------------------------------------------------------------------

-- Étape 1 : bras robotisés, 4 directions, d'un coffre (toujours plein) à un coffre (toujours vidé).
local function build_inserters(x0, y0)
  local names = { "burner-inserter", "inserter", "long-handed-inserter", "fast-inserter", "bulk-inserter" }
  power({ x0 + 4, y0 + 7 }, { { x0 + 11, y0 + 7 }, { x0 + 25, y0 + 7 }, { x0 + 11, y0 + 20 }, { x0 + 25, y0 + 20 },
    { x0 + 11, y0 + 33 }, { x0 + 25, y0 + 33 } })
  for r, name in ipairs(names) do
    local cy = y0 + 3.5 + (r - 1) * 6.5
    for d, dir in ipairs(DIRS) do
      local cx = x0 + 8.5 + (d - 1) * 7
      local ins = create { name = name, position = { cx, cy }, direction = dir[2] }
      if ins then
        if name == "burner-inserter" then keep(ins, { fuel = true }) end
        keep(chest_at("iron-chest", ins.pickup_position), { input = { "iron-plate", 400 } })
        keep(chest_at("wooden-chest", ins.drop_position), { clear = true })
      end
      if r == 1 then label(dir[1], cx, y0 - 0.8, 0.6) end
    end
    label(name, x0 + 33, cy - 0.5, 0.7, "left")
  end
end

-- Étape 1 : assembleurs 1 à 3 au travail.
local function build_assemblers(x0, y0)
  power({ x0 + 1, y0 + 6 }, { { x0 + 4, y0 + 6 }, { x0 + 20, y0 + 6 } })
  for n = 1, 3 do
    local x = x0 + 8.5 + (n - 1) * 8
    local a = create { name = "assembling-machine-" .. n, position = { x, y0 + 6.5 } }
    if a then a.set_recipe("iron-gear-wheel"); keep(a, { clear = true }) end
    keep(create { name = "iron-chest", position = { x, y0 + 2.5 } }, { input = { "iron-plate", 400 } })
    create { name = "fast-inserter", position = { x, y0 + 3.5 }, direction = S }
    create { name = "fast-inserter", position = { x, y0 + 9.5 }, direction = S }
    keep(create { name = "wooden-chest", position = { x, y0 + 10.5 } }, { clear = true })
    label("assembling-machine-" .. n, x, y0 + 11.6, 0.6)
  end
end

-- Étape 1 : poteaux électriques et câbles (lignes reliées).
local function build_poles(x0, y0)
  local lines = { { "small-electric-pole", 6 }, { "medium-electric-pole", 8 }, { "big-electric-pole", 14 },
    { "substation", 14 } }
  for i, l in ipairs(lines) do
    local y = y0 + 2 + (i - 1) * 5
    for k = 0, 3 do create { name = l[1], position = { x0 + 2 + k * l[2], y } } end
    label(l[1], x0 + 2 + 3 * l[2] + 4, y - 0.5, 0.7, "left")
  end
end

-- Étape 1 : minerais, chaque étape de richesse (du plus petit tas au plus gros), puis un gisement.
local function build_ores(x0, y0)
  for i, name in ipairs({ "iron-ore", "copper-ore", "coal", "stone", "uranium-ore" }) do
    local y = y0 + 1 + (i - 1) * 3.5
    local counts = get(prototypes.entity[name], "stage_counts") or { 15000, 9500, 5500, 2900, 1300, 400, 150, 80 }
    for k = #counts, 1, -1 do
      create { name = name, position = { x0 + 1.5 + (#counts - k), y + 0.5 }, amount = counts[k], force = "neutral" }
    end
    for dx = 0, 17 do for dy = 0, 2 do
      create { name = name, position = { x0 + 11.5 + dx, y + dy + 0.5 }, force = "neutral",
        amount = 2000 + (dx * 7 + dy * 13) % 9 * 2000 }
    end end
    label(name, x0 + 5, y + 1.3, 0.7)
  end
end

-- Étape 1 : les sols de Nauvis côte à côte (on y voit les transitions).
local function build_grounds(x0, y0)
  local names = { "grass-1", "grass-2", "grass-3", "grass-4", "dry-dirt", "dirt-1", "dirt-2", "dirt-3", "dirt-4",
    "dirt-5", "dirt-6", "dirt-7", "sand-1", "sand-2", "sand-3", "red-desert-0", "red-desert-1", "red-desert-2",
    "red-desert-3", "water", "deepwater", "water-green", "water-shallow", "water-mud" }
  for i, name in ipairs(names) do
    local k = i - 1
    local x, y = x0 + (k % 6) * 8, y0 + math.floor(k / 6) * 7
    tiles(name, x, y, x + 7, y + 5)
    label(name, x + 3.5, y + 5.1, 0.6)
  end
end

------------------------------------------------------------------------------------------------------------------------

-- Lot 2.1 : les objets intermédiaires, chacun tournant sur sa petite boucle.
local LOT_ITEMS = { "iron-plate", "copper-plate", "steel-plate", "iron-gear-wheel", "copper-cable", "iron-stick",
  "electronic-circuit", "advanced-circuit", "processing-unit", "stone-brick", "wood", "plastic-bar", "sulfur",
  "battery", "engine-unit", "electric-engine-unit", "flying-robot-frame", "low-density-structure", "rocket-fuel",
  "solid-fuel", "explosives", "uranium-235", "uranium-238", "automation-science-pack", "logistic-science-pack",
  "military-science-pack", "chemical-science-pack", "production-science-pack", "utility-science-pack",
  "space-science-pack" }

local function build_items(x0, y0)
  for i, name in ipairs(LOT_ITEMS) do
    local col, row = math.floor((i - 1) / 10), (i - 1) % 10
    local x, y = x0 + col * 16, y0 + row * 3.5
    if prototypes.item[name] then belt_loop("transport-belt", x, y, 5, 2, false, nil, { name }) end
    label(name, x + 5.6, y + 0.4, 0.6, "left")
  end
end

-- Lot 2.2 : fours en pierre, foreuses à charbon, foreuses électriques (sèches et humides), 4 directions.
local function build_production(x0, y0)
  for k = 0, 2 do
    local f = create { name = "stone-furnace", position = { x0 + 3 + k * 4, y0 + 2 } }
    if f and k > 0 then keep(f, { fuel = true, input = { k == 1 and "iron-ore" or "copper-ore", 50 }, clear = true }) end
  end
  label("stone-furnace (éteint, fer, cuivre)", x0 + 7, y0 + 3.4, 0.6)
  ore("iron-ore", x0, y0 + 7, x0 + 18, y0 + 13)
  for k, d in ipairs(DIRS) do
    local e = create { name = "burner-mining-drill", position = { x0 + 2 + (k - 1) * 5, y0 + 10 }, direction = d[2] }
    if e then
      keep(e, { fuel = true })
      keep(chest_at("wooden-chest", e.drop_position), { clear = true })
    end
    label(d[1], x0 + 2 + (k - 1) * 5, y0 + 13.2, 0.5)
  end
  label("burner-mining-drill", x0 + 9, y0 + 14, 0.6)
  power({ x0 + 25, y0 + 2 }, { { x0 + 31, y0 + 2 }, { x0 + 31, y0 + 15 }, { x0 + 31, y0 + 28 } })
  ore("copper-ore", x0 + 21, y0 + 4, x0 + 41, y0 + 14)
  ore("uranium-ore", x0 + 21, y0 + 17, x0 + 41, y0 + 27)
  for row = 0, 1 do
    for k, d in ipairs(DIRS) do
      local x, y = x0 + 22.5 + (k - 1) * 5, y0 + 8.5 + row * 13
      local e = create { name = "electric-mining-drill", position = { x, y }, direction = d[2] }
      if e then
        if row == 1 then keep(e, { fluid = { "sulfuric-acid", 100 } }) end
        keep(chest_at("wooden-chest", e.drop_position), { clear = true })
      end
      label(d[1], x, y + 2.6, 0.5)
    end
  end
  label("electric-mining-drill", x0 + 31, y0 + 14.2, 0.6)
  label("electric-mining-drill (humide : uranium, acide)", x0 + 31, y0 + 27.2, 0.6)
end

-- Lot 2.3 : coffres en bois, fer et acier : seuls, en rangées jointives, et en service.
local function build_storage(x0, y0)
  local chests = { "wooden-chest", "iron-chest", "steel-chest" }
  for k, name in ipairs(chests) do
    local x = x0 + 1 + (k - 1) * 11
    create { name = name, position = { x + 0.5, y0 + 1.5 } }
    label(name, x + 0.5, y0 + 2.6, 0.5)
    for i = 0, 5 do create { name = name, position = { x + i + 0.5, y0 + 5.5 } } end
    for i = 0, 1 do for j = 0, 1 do create { name = name, position = { x + 7 + i + 0.5, y0 + 0.5 + j } } end end
  end
  power({ x0 + 34, y0 + 9 }, { { x0 + 5, y0 + 12 }, { x0 + 16, y0 + 12 }, { x0 + 27, y0 + 12 } })
  for k, name in ipairs(chests) do
    local x = x0 + 1 + (k - 1) * 11
    keep(create { name = name, position = { x + 0.5, y0 + 9.5 } }, { input = { "iron-plate", 400 } })
    create { name = "fast-inserter", position = { x + 1.5, y0 + 9.5 }, direction = W }
    for i = 2, 5 do create { name = "transport-belt", position = { x + i + 0.5, y0 + 9.5 }, direction = E } end
    create { name = "fast-inserter", position = { x + 6.5, y0 + 9.5 }, direction = W }
    keep(create { name = chests[k % 3 + 1], position = { x + 7.5, y0 + 9.5 } }, { clear = true })
  end
end

-- Lot 2.4 : chaudières dans les 4 directions (allumées, puis éteintes), eau fournie et vapeur évacuée par des
-- tuyaux infinis ; à droite, une vraie chaîne : pompe côtière, chaudière, deux machines à vapeur qui débitent.
local function turn(d, dx, dy)   -- décalage donné pour le nord, tourné vers la direction d
  if d == E then return -dy, dx elseif d == S then return -dx, -dy elseif d == W then return dy, -dx end
  return dx, dy
end

local function infinity(x, y, fluid, remove)
  local p = create { name = "infinity-pipe", position = { x, y } }
  if p then pcall(function() p.set_infinity_pipe_filter { name = fluid, percentage = remove and 0 or 1,
    mode = remove and "exactly" or "at-least" } end) end
end

local function build_steam(x0, y0)
  local spots = { { 5.5, 4 }, { 14, 4.5 }, { 22.5, 4 }, { 30, 4.5 } }
  for k, d in ipairs(DIRS) do
    local cx, cy = x0 + spots[k][1], y0 + spots[k][2]
    for row = 0, 1 do
      local y = cy + row * 8
      local b = create { name = "boiler", position = { cx, y }, direction = d[2] }
      if b and row == 0 then keep(b, { fuel = true }) end
      for _, side in ipairs({ -1, 1 }) do
        local dx, dy = turn(d[2], side * 2, 0.5)
        infinity(cx + dx, y + dy, "water")
      end
      local dx, dy = turn(d[2], 0, -1.5)
      infinity(cx + dx, y + dy, "steam", true)
    end
    label(d[1], cx, cy + 2.8, 0.5)
  end
  label("boiler : allumées (haut), éteintes (bas)", x0 + 18, y0 + 15.5, 0.6)
  -- chaîne complète
  local bx, by = x0 + 46.5, y0 + 14
  tiles("water", x0 + 38, y0 + 17, x0 + 56, y0 + 22)
  local b = create { name = "boiler", position = { bx, by }, direction = N }
  keep(b, { fuel = true })
  create { name = "steam-engine", position = { bx, by - 3.5 }, direction = N }
  create { name = "steam-engine", position = { bx, by - 8.5 }, direction = N }
  local px = bx - 2
  local pump
  for _, y in ipairs({ y0 + 17.5, y0 + 17, y0 + 18, y0 + 18.5 }) do
    if surface.can_place_entity { name = "offshore-pump", position = { px, y }, direction = N, force = "player" } then
      pump = create { name = "offshore-pump", position = { px, y }, direction = N }
      break
    end
  end
  if not pump then note("échec : offshore-pump (pas de place sur la rive)") end
  for y = by + 0.5, by + 6.5 do       -- tuyaux de la pompe à l'entrée d'eau de la chaudière, jusqu'à la pompe
    if not surface.can_place_entity { name = "pipe", position = { px, y }, force = "player" } then break end
    create { name = "pipe", position = { px, y } }
  end
  -- consommateur : les machines à vapeur tournent
  create { name = "small-electric-pole", position = { bx + 2, by - 6.5 } }
  local eei = create { name = "electric-energy-interface", position = { bx + 3.5, by - 7 } }
  if eei then pcall(function() eei.power_production = 0; eei.power_usage = 1.8e6; eei.electric_buffer_size = 1e7 end) end
  label("pompe côtière, chaudière, machines à vapeur", bx, y0 + 22.3, 0.6)
end

------------------------------------------------------------------------------------------------------------------------

-- Lot 2.7 : arbres de Nauvis (deux de chaque), gros rochers, étang à poissons.
local function build_nature(x0, y0)
  local names = {}
  for name, p in pairs(prototypes.entity) do
    if p.type == "tree" and (name:match("^tree%-") or name:match("dead") or name:match("dry")) then
      names[#names + 1] = name
    end
  end
  table.sort(names)
  for i, name in ipairs(names) do
    local k = i - 1
    local x, y = x0 + (k % 7) * 6.3, y0 + math.floor(k / 7) * 6
    create { name = name, position = { x + 1.5, y + 3 }, force = "neutral" }
    create { name = name, position = { x + 4.5, y + 3 }, force = "neutral" }
    label(name, x + 3, y + 4.6, 0.45)
  end
  local ry = y0 + math.ceil(#names / 7) * 6 + 1
  tiles("sand-1", x0, ry + 10, x0 + 24, ry + 15)
  for i, name in ipairs({ "big-rock", "huge-rock", "big-sand-rock" }) do
    for j = 0, 4 do
      local x, y = x0 + j * 4.6 + 2.4, ry + (i - 1) * 5.4 + 2
      create { name = name, position = { x, y }, force = "neutral" }
      local grass = i == 3 and "white-desert-bush" or "green-hairy-grass"
      decoratives { { name = grass, position = { x - 1.6, y + 1.2 }, amount = 1 },
        { name = grass, position = { x + 1.7, y - 0.6 }, amount = 1 } }
    end
    label(name, x0 + 11, ry + (i - 1) * 5.4 + 3.8, 0.5)
  end
  tiles("water", x0 + 28, ry, x0 + 42, ry + 14)
  for k = 0, 7 do create { name = "fish", position = { x0 + 30.5 + (k % 3) * 4, ry + 2 + math.floor(k / 3) * 4 } } end
end

-- Lot 2.8 : décorations de Nauvis (plantes, cailloux, taches), trois exemplaires de chaque.
local NAUVIS_DECORATIVES = { "green-hairy-grass", "green-carpet-grass", "green-small-grass", "brown-hairy-grass",
  "brown-carpet-grass", "green-asterisk", "green-asterisk-mini", "brown-asterisk", "brown-asterisk-mini",
  "red-asterisk", "green-pita", "green-pita-mini", "red-pita", "brown-fluff", "brown-fluff-dry", "green-bush-mini",
  "garballo", "garballo-mini-dry", "green-croton", "red-croton", "green-desert-bush", "red-desert-bush",
  "white-desert-bush", "small-rock", "tiny-rock", "medium-rock", "medium-sand-rock", "muddy-stump",
  "light-mud-decal", "dark-mud-decal", "cracked-mud-decal", "red-desert-decal", "sand-decal", "sand-dune-decal",
  "lichen-decal", "shroom-decal", "worms-decal" }

local function build_decoratives(x0, y0)
  for i, name in ipairs(NAUVIS_DECORATIVES) do
    local k = i - 1
    local x, y = x0 + (k % 6) * 5.6, y0 + math.floor(k / 6) * 4.6
    if prototypes.decorative[name] then
      decoratives { { name = name, position = { x + 1, y + 1 }, amount = 1 },
        { name = name, position = { x + 3, y + 1.5 }, amount = 1 }, { name = name, position = { x + 2, y + 2.6 }, amount = 1 } }
    end
    label(name, x + 2.6, y + 3.6, 0.4)
  end
end

-- Lot 2.8 (tri par profondeur) : herbes autour de cailloux, d'arbres et de rochers ; convoyeur posé sur des décorations.
local function build_overlaps(x0, y0)
  local rocks = { "medium-rock", "small-rock", "tiny-rock", "medium-sand-rock" }
  local grasses = { "green-hairy-grass", "green-small-grass", "brown-hairy-grass", "green-croton", "green-pita",
    "green-bush-mini" }
  for i, rock in ipairs(rocks) do
    for j, grass in ipairs(grasses) do
      local x, y = x0 + (j - 1) * 5.6 + 2.6, y0 + (i - 1) * 4.5 + 1.5
      local list = { { name = rock, position = { x, y }, amount = 1 } }
      for k, d in ipairs({ { 0, -0.7 }, { -0.8, 0 }, { 0.8, 0 }, { 0, 0.7 }, { -0.5, 0.9 }, { 0.5, -0.9 } }) do
        list[k + 1] = { name = grass, position = { x + d[1], y + d[2] }, amount = 1 }
      end
      decoratives(list)
      label(rock .. " / " .. grass, x, y + 1.5, 0.3)
    end
  end
  local things = { "tree-01", "tree-05", "tree-08", "big-rock", "huge-rock", "tree-02" }
  for i, name in ipairs(things) do
    local x, y = x0 + (i - 1) * 5.6 + 2.6, y0 + 23
    create { name = name, position = { x, y }, force = "neutral" }
    local list = {}
    for k = 0, 15 do
      local a, d = k * math.pi / 8, 1.4 + (k % 2) * 0.8
      list[#list + 1] = { name = (k % 3 == 0) and "medium-rock" or "green-hairy-grass",
        position = { x + math.cos(a) * d, y + math.sin(a) * d * 0.9 }, amount = 1 }
    end
    decoratives(list)
  end
  for i = 0, 31 do
    local x, y = x0 + i + 1.5, y0 + 28.5
    decoratives { { name = (i % 4 == 0) and "medium-rock" or "green-hairy-grass",
      position = { x, y - 0.6 + (i % 3) * 0.6 }, amount = 1 } }
    create { name = "transport-belt", position = { x, y }, direction = E }
  end
end

------------------------------------------------------------------------------------------------------------------------
-- Les zones, dans l'ordre du plan (docs/cartoon/plan.md). w, h : taille en cases.

local ZONES = {
  { id = "convoyeurs", titre = "Étape 1 · Convoyeurs, souterrains, répartiteurs", w = 64, h = 20, build = build_belts },
  { id = "bras", titre = "Étape 1 · Bras robotisés", w = 48, h = 34, build = build_inserters },
  { id = "assembleurs", titre = "Étape 1 · Assembleurs", w = 30, h = 13, build = build_assemblers },
  { id = "pylones", titre = "Étape 1 · Poteaux et câbles", w = 64, h = 20, build = build_poles },
  { id = "minerais", titre = "Étape 1 · Minerais", w = 30, h = 19, build = build_ores },
  { id = "sols", titre = "Étape 1 · Sols", w = 48, h = 28, build = build_grounds },
  { id = "objets", titre = "Lot 2.1 · Objets sur les convoyeurs", w = 46, h = 35, build = build_items },
  { id = "production", titre = "Lot 2.2 · Production de base", w = 42, h = 28, build = build_production },
  { id = "stockage", titre = "Lot 2.3 · Stockage", w = 36, h = 13, build = build_storage },
  { id = "energie", titre = "Lot 2.4 · Énergie vapeur (chaudière et machine à vapeur faites ; pompe côtière à venir)",
    w = 56, h = 23, build = build_steam },
  { id = "nature", titre = "Lot 2.7 · Nature", w = 44, h = 38, build = build_nature },
  { id = "decorations", titre = "Lot 2.8 · Décorations", w = 34, h = 32, build = build_decoratives },
  { id = "superpositions", titre = "Lot 2.8 · Superpositions (tri par profondeur)", w = 34, h = 30,
    build = build_overlaps },
}

-- Range les zones en lignes de ROW_WIDTH cases au plus ; renvoie la taille totale.
local function layout()
  local x, y, row_h, width = 0, GAP_Y, 0, 0
  for _, z in ipairs(ZONES) do
    if x > 0 and x + z.w > ROW_WIDTH then x, y, row_h = 0, y + row_h + GAP_Y, 0 end
    z.x, z.y = x, y
    x, row_h = x + z.w + GAP_X, math.max(row_h, z.h)
    width = math.max(width, x - GAP_X)
  end
  return width, y + row_h
end

local function nauvis_setup()
  surface = game.surfaces.nauvis
  local settings = surface.map_gen_settings
  settings.autoplace_controls = settings.autoplace_controls or {}
  settings.autoplace_controls["enemy-base"] = { frequency = 0, size = 0, richness = 0 }
  surface.map_gen_settings = settings
  surface.peaceful_mode = true
  surface.always_day = true
  game.map_settings.enemy_expansion.enabled = false
  game.map_settings.pollution.enabled = false
end

local function build()
  nauvis_setup()
  local width, height = layout()
  local x1, y1, x2, y2 = -8, -14, width + 8, height + 8
  surface.request_to_generate_chunks({ (x1 + x2) / 2, (y1 + y2) / 2 }, math.ceil(math.max(x2 - x1, y2 - y1) / 64) + 2)
  surface.force_generate_chunk_requests()
  local area = { { x1, y1 }, { x2, y2 } }
  for _, e in pairs(surface.find_entities_filtered { area = area }) do
    if e.valid and e.type ~= "character" then e.destroy() end
  end
  surface.destroy_decoratives { area = area }
  tiles(GROUND, x1, y1, x2, y2)

  label("Galerie du mod cartoon", width / 2, -11, 3)
  label(CARTOON and "Mod cartoon actif" or "Mod cartoon inactif : graphismes d'origine", width / 2, -6, 1)
  label("Fenêtre « Galerie » en haut à gauche pour aller à une zone", width / 2, -4, 0.7)
  storage.keep = {}
  storage.zones = {}
  for _, z in ipairs(ZONES) do
    label(z.titre, z.x + z.w / 2, z.y - 5, 1.3)
    rendering.draw_rectangle { surface = surface, color = { 1, 1, 1, 0.35 }, width = 2, filled = false,
      left_top = { z.x - 1, z.y - 1 }, right_bottom = { z.x + z.w + 1, z.y + z.h + 1 } }
    local ok, err = pcall(z.build, z.x, z.y)
    if not ok then note("ERREUR " .. z.id .. " : " .. tostring(err)) end
    storage.zones[#storage.zones + 1] = { id = z.id, titre = z.titre, x = z.x, y = z.y, w = z.w, h = z.h }
  end
  storage.spawn = { width / 2, -1 }
  game.forces.player.set_spawn_position(storage.spawn, surface)
  game.forces.player.chart(surface, area)
  pcall(function() game.forces.player.research_all_technologies() end)
  storage.tags_pending = true
  refill()
end

------------------------------------------------------------------------------------------------------------------------
-- Fenêtre « Galerie »

local function go(player, pos)
  local free = surface.find_non_colliding_position("character", pos, 12, 0.5) or pos
  player.teleport(free, surface)
end

local function gui(player)
  if player.gui.left.galerie then player.gui.left.galerie.destroy() end
  local f = player.gui.left.add { type = "frame", name = "galerie", caption = "Galerie", direction = "vertical" }
  f.add { type = "label", caption = CARTOON and "Mod cartoon actif" or "Mod cartoon inactif (origine)" }
  for i, z in ipairs(storage.zones) do
    f.add { type = "button", caption = z.titre, tags = { galerie = "zone", zone = i } }.style.horizontally_stretchable = true
  end
  f.add { type = "button", caption = "Accueil", tags = { galerie = "accueil" } }
  f.add { type = "checkbox", caption = "Toujours le jour", state = surface.always_day, tags = { galerie = "jour" } }
  f.add { type = "button", caption = "Mode éditeur (activer / quitter)", tags = { galerie = "editeur" } }
  f.add { type = "button", caption = "Réduire", tags = { galerie = "reduire" } }
end

local function small_gui(player)
  if player.gui.left.galerie then player.gui.left.galerie.destroy() end
  player.gui.left.add { type = "button", name = "galerie", caption = "Galerie", tags = { galerie = "ouvrir" } }
end

script.on_event(defines.events.on_gui_click, function(event)
  local action = event.element.valid and event.element.tags.galerie
  if not action then return end
  local player = game.get_player(event.player_index)
  surface = game.surfaces.nauvis
  if action == "zone" then
    local z = storage.zones[event.element.tags.zone]
    go(player, { z.x + z.w / 2, z.y + z.h / 2 })
  elseif action == "accueil" then
    go(player, storage.spawn)
  elseif action == "editeur" then
    player.toggle_map_editor()
  elseif action == "reduire" then
    small_gui(player)
  elseif action == "ouvrir" then
    gui(player)
  end
end)

script.on_event(defines.events.on_gui_checked_state_changed, function(event)
  if event.element.valid and event.element.tags.galerie == "jour" then
    game.surfaces.nauvis.always_day = event.element.state
  end
end)

script.on_event(defines.events.on_player_created, function(event)
  local player = game.get_player(event.player_index)
  surface = game.surfaces.nauvis
  player.cheat_mode = true
  go(player, storage.spawn)
  gui(player)
end)

-- Pas d'ennemis, même loin de la galerie.
script.on_event(defines.events.on_chunk_generated, function(event)
  for _, e in pairs(event.surface.find_entities_filtered { area = event.area, force = "enemy" }) do e.destroy() end
end)

script.on_init(function()
  build()
  if BENCH then helpers.write_file("galerie/" .. VARIANT .. "/journal.txt", table.concat(log_lines, "\n") .. "\n") end
  for _, l in ipairs(log_lines) do log("galerie : " .. l) end
end)

script.on_nth_tick(REFILL_TICKS, refill)

------------------------------------------------------------------------------------------------------------------------
-- Repères sur la carte (une fois la zone cartographiée) et captures pour le banc d'essai.

local SHOT_TICK = 300

local function shoot(name, x, y, w, h, zoom)
  game.take_screenshot { surface = game.surfaces.nauvis, position = { x + w / 2, y + h / 2 }, zoom = zoom,
    resolution = { math.floor(w * 32 * zoom), math.floor(h * 32 * zoom) },
    path = "galerie/" .. VARIANT .. "/" .. name .. ".png", daytime = 0, show_entity_info = false, force_render = true }
end

script.on_event(defines.events.on_tick, function(event)
  if storage.tags_pending and event.tick % 60 == 30 then
    local s = game.surfaces.nauvis
    local done = true
    for _, z in ipairs(storage.zones) do
      if not z.tag then
        local ok, tag = pcall(game.forces.player.add_chart_tag, s,
          { position = { z.x + z.w / 2, z.y - 2 }, text = z.titre })
        if ok and tag then z.tag = true else done = false end
      end
    end
    if done or event.tick > 3600 then storage.tags_pending = false end
  end
  if not BENCH then return end
  if event.tick == SHOT_TICK then
    for _, z in ipairs(storage.zones) do shoot(z.id, z.x - 2, z.y - 6, z.w + 4, z.h + 8, 1) end
    local width, height = 0, 0
    for _, z in ipairs(storage.zones) do width, height = math.max(width, z.x + z.w), math.max(height, z.y + z.h) end
    shoot("ensemble", -8, -12, width + 16, height + 20, 0.25)
    game.set_wait_for_screenshots_to_finish()
  elseif event.tick == SHOT_TICK + 10 then
    helpers.write_file("galerie/" .. VARIANT .. "/fini.txt", "ok\n")
  end
end)
