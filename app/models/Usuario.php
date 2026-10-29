const usuarios = [
  { id: 1, nombre: "Ana" },
  { id: 2, nombre: "Luis" }
];

module.exports = {
  obtenerTodos: () => usuarios,
  obtenerPorId: (id) => usuarios.find(u => u.id === id)
};
