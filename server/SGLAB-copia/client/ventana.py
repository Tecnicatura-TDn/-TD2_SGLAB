#!/usr/bin/env python3
"""Captura manual de SGLAB con cédula y laboratorio (interfaz provisional)."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk


def validar(ci, laboratorio):
    ci = ci.strip()
    laboratorio = laboratorio.strip()
    if not ci.isascii() or not ci.isdecimal() or not 1 <= int(ci) <= 4294967295:
        raise ValueError('Ingresá la cédula solo con números, sin puntos ni guion.')
    if not 1 <= len(laboratorio) <= 20:
        raise ValueError('El laboratorio debe tener entre 1 y 20 caracteres.')
    return int(ci), laboratorio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    defecto = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'SGLAB' / 'cliente.json'
    parser.add_argument('--config', type=Path, default=defecto)
    args = parser.parse_args()
    ventana = tk.Tk()
    ventana.title('SGLAB - Registrar captura')
    ventana.resizable(False, False)
    panel = ttk.Frame(ventana, padding=24)
    panel.grid()
    ttk.Label(panel, text='Registro de esta PC', font=('Segoe UI', 15, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 15))
    try:
        config = json.loads(args.config.read_text(encoding='utf-8'))
        if not isinstance(config, dict):
            raise ValueError('Configuración inválida')
    except (OSError, ValueError) as exc:
        messagebox.showerror('SGLAB', f'Primero instalá el cliente SGLAB.\nNo se pudo leer la configuración:\n{exc}')
        ventana.destroy()
        return 1
    ci = tk.StringVar()
    laboratorio = tk.StringVar(value=str(config.get('laboratorio', '')))
    ttk.Label(panel, text='Cédula (solo números)').grid(row=1, column=0, sticky='w', padx=(0, 15), pady=6)
    entrada_ci = ttk.Entry(panel, textvariable=ci, width=28)
    entrada_ci.grid(row=1, column=1, pady=6)
    ttk.Label(panel, text='Laboratorio').grid(row=2, column=0, sticky='w', pady=6)
    entrada_lab = ttk.Entry(panel, textvariable=laboratorio, width=28)
    entrada_lab.grid(row=2, column=1, pady=6)
    ttk.Label(panel, text='Estos datos se guardarán en la captura TOML.\nLa cédula es declarada; no verifica tu identidad.').grid(row=3, column=0, columnspan=2, sticky='w', pady=12)
    estado = tk.StringVar(value='Completá los datos y presioná Recopilar y enviar.')
    ttk.Label(panel, textvariable=estado, wraplength=420).grid(row=5, column=0, columnspan=2, sticky='w', pady=(12, 0))
    resultados = []
    ocupado = False

    def terminado():
        nonlocal ocupado
        if not resultados:
            ventana.after(100, terminado)
            return
        codigo, salida = resultados.pop()
        ocupado = False
        boton.config(state='normal')
        entrada_ci.config(state='normal')
        entrada_lab.config(state='normal')
        estado.set('Captura completada.' if codigo == 0 else 'No se pudo completar. Revisá el detalle.')
        if codigo == 0:
            messagebox.showinfo('SGLAB - Resultado', salida or 'Captura completada.')
        else:
            messagebox.showerror('SGLAB - Resultado', salida or 'Error al ejecutar el recolector.')

    def iniciar():
        nonlocal ocupado
        if ocupado:
            return
        try:
            cedula, lab = validar(ci.get(), laboratorio.get())
        except ValueError as exc:
            messagebox.showerror('Revisá los datos', str(exc))
            return
        ocupado = True
        boton.config(state='disabled')
        entrada_ci.config(state='disabled')
        entrada_lab.config(state='disabled')
        estado.set('Recopilando y enviando… Puede demorar unos minutos.')
        def trabajar():
            try:
                # Usar python.exe para capturar stdout; pythonw.exe no abre consola.
                python = Path(sys.executable)
                if python.name.lower() == 'pythonw.exe':
                    python = python.with_name('python.exe')
                comando = [str(python), str(Path(__file__).with_name('recopilar.py')),
                           '--config', str(args.config.resolve()), '--ci', str(cedula), '--laboratorio', lab]
                opciones = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                r = subprocess.run(comando, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                   env=dict(os.environ, PYTHONIOENCODING='utf-8'), **opciones)
                resultados.append((r.returncode, (r.stdout + '\n' + r.stderr).strip()))
            except OSError as exc:
                resultados.append((1, str(exc)))
        threading.Thread(target=trabajar, daemon=True).start()
        ventana.after(100, terminado)

    def cerrar():
        if ocupado:
            messagebox.showinfo('SGLAB', 'Esperá a que termine la captura y el envío antes de cerrar.')
        else:
            ventana.destroy()
    boton = ttk.Button(panel, text='Recopilar y enviar', command=iniciar)
    boton.grid(row=4, column=0, columnspan=2, sticky='ew')
    ventana.protocol('WM_DELETE_WINDOW', cerrar)
    entrada_ci.focus_set()
    ventana.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
