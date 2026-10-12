-- Teintes des arbres : le jeu teinte le feuillage d'une couleur tirée au hasard dans `colors`.
-- Le feuillage cel-shading est rendu en tons neutres ; certaines teintes d'origine, ternes, le rendent gris :
-- on les remplace par des tons d'automne (choix de Bastien, 12 octobre).
local AUTOMNE = {
  -- [arbre] = { [rang dans colors] = couleur }
  ["tree-02"] = { [2] = { r = 255, g = 150, b = 60 } },   -- (209, 200, 152) beige-gris -> orange d'automne
}

for name, colors in pairs(AUTOMNE) do
  local tree = data.raw.tree[name]
  if tree and tree.colors then
    for i, c in pairs(colors) do
      if tree.colors[i] then tree.colors[i] = c end
    end
  end
end
