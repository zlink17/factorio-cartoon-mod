-- Décorations de Nauvis triées par profondeur, en deux couches sous les entités (lu par data-final-fixes.lua) :
-- - herbes : plusieurs touffes par image, triée d'un bloc sur sa touffe la plus basse ; couche « remnants » ;
-- - un seul élément par image (cailloux, buissons, rameaux, souche) : couche « floor », au-dessus, pour qu'une
--   touffe ne passe jamais sur un caillou ou un buisson dont elle est derrière.
return {
  grasses = { "green-hairy-grass", "green-carpet-grass", "green-small-grass", "brown-hairy-grass",
    "brown-carpet-grass" },
  singles = { "green-asterisk", "green-asterisk-mini", "brown-asterisk", "brown-asterisk-mini", "red-asterisk",
    "green-pita", "green-pita-mini", "red-pita", "brown-fluff", "brown-fluff-dry", "green-bush-mini", "garballo",
    "garballo-mini-dry", "green-croton", "red-croton", "green-desert-bush", "red-desert-bush", "white-desert-bush",
    "small-rock", "tiny-rock", "medium-rock", "medium-sand-rock", "small-sand-rock", "muddy-stump" },
}
