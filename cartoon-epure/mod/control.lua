-- /cartoon-epure : refait les décorations de Nauvis sur toute la surface du joueur avec les densités réglées.
-- Rien n'est fait automatiquement : une partie existante ne change que si on lance la commande (et qu'on sauvegarde).
local families = require("decoratives")

commands.add_command("cartoon-epure", { "command-help.cartoon-epure" }, function(event)
  local player = event.player_index and game.get_player(event.player_index)
  local surface = player and player.surface or game.surfaces.nauvis
  local names = {}
  for _, list in pairs(families) do
    for _, name in pairs(list) do
      if prototypes.decorative[name] then names[#names + 1] = name end
    end
  end
  -- regenerate_decorative ajoute sans retirer l'existant : on supprime d'abord ces décorations sur toute la surface
  surface.destroy_decoratives { name = names }
  surface.regenerate_decorative(names)
  game.print({ "cartoon-epure.done", surface.name })
end)
