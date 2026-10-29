const Usuario = require("../models/Usuario");

exports.listar = (req, res) => {
  const usuarios = Usuario.obtenerTodos();
  res.render("usuarios/index", { usuarios });
};

exports.detalle = (req, res) => {
  const usuario = Usuario.obtenerPorId(Number(req.params.id));
  if (!usuario) return res.status(404).send("Usuario no encontrado");
  res.render("usuarios/detalle", { usuario });
};
