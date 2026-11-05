#!/bin/sh
# Ejecutar dentro del contenedor de prueba, nunca en el servidor real.
set -eu
[ -f /.dockerenv ] || exit 1
printf "127.0.0.1 %s\n" "$(hostname)" >> /etc/hosts
. /prueba/setup_sglab.sh
log() { printf '%s\n' "$1"; }
info() { printf '%s\n' "$1"; }
warn() { printf '%s\n' "$1"; }

# Solo reemplazamos el pedido interactivo de contraseña durante esta prueba.
password_calls=0
sudo() {
    if [ "$1" = passwd ] && [ "$#" = 2 ]; then
        password_calls=$((password_calls + 1))
        printf '%s:%s\n' "$2" 'ClaveSoloDelContenedor123' | chpasswd
    else
        command sudo "$@"
    fi
}

groupadd docker
useradd -m -s /bin/bash BASE-TD2
preparar_receptor
[ "$password_calls" = 1 ]
id -nG BASE-TD2 | tr ' ' '\n' | grep -qx sglab-ingest
! id -nG BASE-TD2 | tr ' ' '\n' | grep -qx docker
printf '# clave anterior\n' >> /home/BASE-TD2/.ssh/authorized_keys
preparar_receptor
[ "$password_calls" = 1 ]
grep -q 'clave anterior' /home/BASE-TD2/.ssh/authorized_keys
[ "$(stat -c %a /home/BASE-TD2/.ssh)" = 700 ]
[ "$(stat -c %a /home/BASE-TD2/.ssh/authorized_keys)" = 600 ]

useradd -m -s /bin/bash administrador
operador=administrador
grupo_operador="$(id -gn "$operador")"
proyecto=/home/administrador/prueba-cola
chmod 700 /home/administrador
install -d -m 0700 -o "$operador" -g "$grupo_operador" "$proyecto"
printf 'CONFIGURACION DE PRUEBA\n' > "$proyecto/.env"
chown "$operador:$grupo_operador" "$proyecto/.env"
mkdir -p "$proyecto/server/bin" "$proyecto/.venv/bin"
printf '#!/bin/sh\n' > "$proyecto/server/bin/spawn.sh"
printf '#!/bin/sh\n' > "$proyecto/.venv/bin/tomlq"
chown -R "$operador:$grupo_operador" "$proyecto"
permisos_cola
# Comprobar con identidades reales de Linux, no solo mirando el chmod.
sudo -u BASE-TD2 -- sh -c 'printf "captura\n" > "$1/prueba.toml.part"; chmod 0640 "$1/prueba.toml.part"; mv "$1/prueba.toml.part" "$1/prueba.toml"' sh "$proyecto/var/incoming"
sudo -u BASE-TD2 -- cat "$proyecto/var/incoming/prueba.toml" >/dev/null
sudo -u BASE-TD2 -- mv "$proyecto/var/incoming/prueba.toml" "$proyecto/var/processing/prueba.toml"
for carpeta in processing processed rejected; do
    sudo -u BASE-TD2 -- test -x "$proyecto/var/$carpeta"
done
! sudo -u BASE-TD2 -- test -r "$proyecto/.env"
! sudo -u BASE-TD2 -- test -w "$proyecto/server/bin/spawn.sh"
sudo -u BASE-TD2 -- test -r "$proyecto/server/bin/spawn.sh"
[ "$(stat -c %a "$proyecto/.env")" = 600 ]

ssh-keygen -q -t ed25519 -N '' -f /tmp/cliente
printf '/tmp/cliente.pub\n' | autorizar_cliente_sglab
printf '/tmp/cliente.pub\n' | autorizar_cliente_sglab
[ "$(grep -c '^restrict ssh-ed25519 ' /home/BASE-TD2/.ssh/authorized_keys)" = 1 ]
if printf '/tmp/cliente\n' | autorizar_cliente_sglab; then exit 1; fi

mv "$proyecto/var/incoming" "$proyecto/var/incoming-real"
ln -s "$proyecto/var/incoming-real" "$proyecto/var/incoming"
if permisos_cola; then exit 1; fi
printf 'OK: contraseña, grupos, claves, permisos de recepción/lectura y procesamiento con BASE-TD2\n'

# Probar la integración de clonación sin acceder a GitHub desde el contenedor.
sudo() {
    if [ "$1" = -H ]; then
        prueba_usuario="$3"
        shift 4
        [ "$1" = git ] || return 1
        shift
        case "$1" in
            clone)
                [ "$2" = -- ] || return 1
                prueba_repo="$3"
                prueba_destino="$4"
                mkdir -p "$prueba_destino/.git" "$prueba_destino/server/SGLAB/server/bin"
                touch "$prueba_destino/server/SGLAB/compose.yaml" "$prueba_destino/server/SGLAB/server/bin/spawn.sh"
                printf '%s\n' "$prueba_repo" > "$prueba_destino/.git/origin-prueba"
                chown -R "$prueba_usuario:$(id -gn "$prueba_usuario")" "$prueba_destino"
                ;;
            -C)
                prueba_destino="$2"
                case "$3" in
                    rev-parse) [ -d "$prueba_destino/.git" ] ;;
                    remote) cat "$prueba_destino/.git/origin-prueba" ;;
                    *) return 1 ;;
                esac
                ;;
            *) return 1 ;;
        esac
    else
        command sudo "$@"
    fi
}
SUDO_USER=administrador
export SUDO_USER
printf '\n' | clonar_repo_sglab
[ "$(stat -c %U /home/administrador/SGLAB)" = administrador ]
if id sglab >/dev/null 2>&1; then exit 1; fi
printf 'cambio local\n' > /home/administrador/SGLAB/conservar.txt
printf '\n' | clonar_repo_sglab
grep -q 'cambio local' /home/administrador/SGLAB/conservar.txt
if printf 'https://github.com/otra/copia.git\n' | clonar_repo_sglab; then exit 1; fi
printf 'OK: clonación bajo administrador, repositorio existente conservado y validaciones\n'
