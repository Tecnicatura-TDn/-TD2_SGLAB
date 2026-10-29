const router = require("express").Router();
const controller = require("../app/controllers/UsuarioController");

router.get("/usuarios", controller.listar);
router.get("/usuarios/:id", controller.detalle);

module.exports = router;
