
crear_memoria() {
    touch ./memoria.txt
    [ -z "$(cat ./memoria.txt)" ] && printf "aprovisionamiento:0" > ./memoria.txt || continue
}

agregar_memoria() {
    # s/ = sustituir.
    # \(aprovisionamiento:\) = crean un grupo de captura.
    # .* = Cualquier cosa que venga después hasta el final.
    # \1 = hace referencia al "Grupo 1" que guardamos antes
    obtener_memoria
    if [ "$memoria" != "0" ] && [ "$1" != "$memoria" ]; then
        sed -i "s/\(aprovisionamiento:\).*/\13/" ./memoria.txt    
    else
        sed -i "s/\(aprovisionamiento:\).*/\1$1/" ./memoria.txt
    fi
    

}

obtener_memoria() {
    memoria=$(grep "aprovisionamiento" ./memoria.txt | cut -d: -f2)
}

operar_memoria() {
    #memoria=$(obtener_memoria)
    obtener_memoria
    if [ "$memoria" = "0" ]; then
        warn "Aún no se a configurado el entorno docker-laravel ó LAMP"
    elif [ "$memoria" = "1" ]; then
        log "Ya se configuró el entorno docker-laravel"
    elif [ "$memoria" = "2" ]; then
        log "Ya se configuró el entorno LAMP"
    elif [ "$memoria" = "3" ]; then
        log "Ya se configuraron los dos entornos docker-laravel y LAMP"
        exit 1
    fi
}
