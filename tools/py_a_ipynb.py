#!/usr/bin/env python3
"""Convierte los notebooks de Fabric (`notebook-content.py`) a `.ipynb`.

El repositorio mantiene los notebooks en dos formatos:

- `fabric/<nombre>.Notebook/notebook-content.py` — el que usa la integración con
  git de Fabric. Es la **fuente de verdad**: es lo que Fabric sincroniza.
- `notebooks/<nombre>.ipynb` — formato Jupyter estándar, para importar a mano,
  abrir en VS Code o leer fuera de Fabric.

Este script genera el segundo a partir del primero. Corre sin dependencias.

    python tools/py_a_ipynb.py            # regenera notebooks/
    python tools/py_a_ipynb.py --check    # falla si están desactualizados (CI)

Si editas un notebook, edita el `.py` y vuelve a correr esto. Al revés no:
los cambios en el `.ipynb` no se propagan.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "fabric"
DESTINO = RAIZ / "notebooks"

# Los marcadores de sección de Fabric llevan exactamente 20 asteriscos.
MARCADOR = re.compile(r"^# (METADATA|MARKDOWN|CELL) \*{20}\s*$")


def separar_secciones(texto: str) -> list[tuple[str, list[str]]]:
    """Parte el archivo en secciones (tipo, líneas) según los marcadores."""
    secciones: list[tuple[str, list[str]]] = []
    tipo: str | None = None
    buffer: list[str] = []

    for linea in texto.splitlines():
        m = MARCADOR.match(linea)
        if m:
            if tipo is not None:
                secciones.append((tipo, buffer))
            tipo, buffer = m.group(1), []
        elif tipo is not None:
            buffer.append(linea)
        # Las líneas antes del primer marcador (`# Fabric notebook source`) se ignoran.

    if tipo is not None:
        secciones.append((tipo, buffer))
    return secciones


def leer_meta(lineas: list[str]) -> dict:
    """Reconstruye el JSON de un bloque `# META`."""
    crudo = "\n".join(l[len("# META ") :] if l.startswith("# META ") else "" for l in lineas)
    crudo = crudo.strip()
    if not crudo:
        return {}
    try:
        return json.loads(crudo)
    except json.JSONDecodeError:
        return {}


def limpiar_markdown(lineas: list[str]) -> list[str]:
    """Quita el prefijo de comentario que Fabric antepone al markdown."""
    salida = []
    for l in lineas:
        if l.startswith("# "):
            salida.append(l[2:])
        elif l.strip() == "#":
            salida.append("")
        else:
            salida.append(l)
    return salida


def recortar(lineas: list[str]) -> list[str]:
    """Elimina líneas en blanco al principio y al final."""
    inicio, fin = 0, len(lineas)
    while inicio < fin and not lineas[inicio].strip():
        inicio += 1
    while fin > inicio and not lineas[fin - 1].strip():
        fin -= 1
    return lineas[inicio:fin]


def a_source(lineas: list[str]) -> list[str]:
    """Formato `source` de nbformat: una entrada por línea, con \\n salvo la última."""
    if not lineas:
        return []
    return [l + "\n" for l in lineas[:-1]] + [lineas[-1]]


def construir(texto: str, nombre: str) -> dict:
    secciones = separar_secciones(texto)

    meta_notebook: dict = {}
    if secciones and secciones[0][0] == "METADATA":
        meta_notebook = leer_meta(secciones[0][1])
        secciones = secciones[1:]

    celdas: list[dict] = []
    for tipo, lineas in secciones:
        if tipo == "METADATA":
            # Pertenece a la celda anterior.
            if celdas:
                meta = leer_meta(lineas)
                if meta:
                    celdas[-1]["metadata"]["microsoft"] = meta
            continue

        contenido = recortar(limpiar_markdown(lineas) if tipo == "MARKDOWN" else lineas)
        if not contenido:
            continue

        if tipo == "MARKDOWN":
            celdas.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": a_source(contenido),
            })
        else:
            # Fabric exige `execution_count: null` y `outputs: []` en toda celda
            # de código; sin eso la importación falla sin detalle del error.
            celdas.append({
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": a_source(contenido),
            })

    return {
        "cells": celdas,
        "metadata": {
            "kernel_info": meta_notebook.get("kernel_info", {"name": "synapse_pyspark"}),
            "kernelspec": {
                "name": "synapse_pyspark",
                "language": "Python",
                "display_name": "Synapse PySpark",
            },
            "language_info": {"name": "python"},
            "dependencies": meta_notebook.get("dependencies", {}),
            "microsoft": {"language": "python", "language_group": "synapse_pyspark"},
            "widgets": {},
            "notebook_name": nombre,
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe nada; devuelve 1 si algún .ipynb está desactualizado.",
    )
    args = parser.parse_args()

    fuentes = sorted(ORIGEN.glob("*.Notebook/notebook-content.py"))
    if not fuentes:
        print(f"No se encontraron notebooks en {ORIGEN}", file=sys.stderr)
        return 1

    DESTINO.mkdir(exist_ok=True)
    desactualizados: list[str] = []

    for fuente in fuentes:
        nombre = fuente.parent.name.removesuffix(".Notebook")
        nb = construir(fuente.read_text(encoding="utf-8"), nombre)
        texto = json.dumps(nb, indent=1, ensure_ascii=False) + "\n"
        salida = DESTINO / f"{nombre}.ipynb"

        n_codigo = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
        n_md = len(nb["cells"]) - n_codigo

        if args.check:
            actual = salida.read_text(encoding="utf-8") if salida.exists() else None
            estado = "OK" if actual == texto else "DESACTUALIZADO"
            if actual != texto:
                desactualizados.append(salida.name)
            print(f"  {estado:14s} {salida.name}")
        else:
            # newline explícito: en Windows, el modo texto de Python traduce cada
            # salto de línea a CRLF y el archivo quedaría distinto de lo que guarda
            # git (.gitattributes fija LF para todo el repositorio).
            salida.write_text(texto, encoding="utf-8", newline="\n")
            print(f"  {salida.name:36s} {n_md:>2} markdown · {n_codigo:>2} código")

    if desactualizados:
        print(
            f"\n{len(desactualizados)} notebook(s) desactualizados. "
            f"Corre: python tools/py_a_ipynb.py",
            file=sys.stderr,
        )
        return 1

    print(f"\n{len(fuentes)} notebooks en {DESTINO.relative_to(RAIZ)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
