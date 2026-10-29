const express = require("express");
const path = require("path");
const usuariosRoutes = require("./routes/usuarios");

const app = express();
const PORT = process.env.PORT || 3000;

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "app", "views"));

app.use(express.static(path.join(__dirname, "public")));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get("/", (req, res) => res.redirect("/usuarios"));
app.use("/", usuariosRoutes);

app.listen(PORT, () => console.log(`Servidor en http://localhost:${PORT}`));
