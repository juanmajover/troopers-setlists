#!/usr/bin/env python3
"""Aplica una acción (proponer/votar/votar_nevera) sobre extra.json.
Ejecutado por el workflow "Candidatas" — es el único código que escribe
en extra.json a partir de lo que dispara cualquiera de los 5 miembros.
"""
import json
import re
import sys
import unicodedata

MIEMBROS = ["JM", "Edu", "Fer", "Fran", "Rafeta"]
RUTA_EXTRA = "extra.json"


def normalizar(s):
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def nombre_candidata(c):
    return c.get("titulo", "") + (" - " + c["artista"] if c.get("artista") else "")


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: candidatas.py '<json>'")
    payload = json.loads(sys.argv[1])
    accion = payload.get("accion")
    miembro = payload.get("miembro") or payload.get("proponente")
    if miembro not in MIEMBROS:
        sys.exit(f"Miembro inválido: {miembro!r}")

    with open(RUTA_EXTRA, encoding="utf-8") as f:
        extra = json.load(f)
    extra.setdefault("candidatas", [])
    extra.setdefault("temas", [])
    extra.setdefault("overrides", {})

    if accion == "proponer":
        titulo = (payload.get("titulo") or "").strip().upper()
        artista = (payload.get("artista") or "").strip()
        if not titulo:
            sys.exit("Falta el título")
        nombre = titulo + (" - " + artista if artista else "")
        clave = normalizar(nombre)
        if any(normalizar(nombre_candidata(c)) == clave for c in extra["candidatas"]):
            print("Ya estaba propuesta — no se duplica")
            return
        if any(normalizar(t.get("nombre", "")) == clave for t in extra["temas"]):
            print("Ese tema ya está en la base — no se propone")
            return
        dur = payload.get("dur")
        extra["candidatas"].append({
            "nombre": nombre,
            "titulo": titulo,
            "artista": artista,
            "afinacion": (payload.get("afinacion") or "").strip().upper(),
            "comentario": (payload.get("comentario") or "").strip(),
            "dur": int(dur) if isinstance(dur, (int, float)) else None,
            "album": payload.get("album") or "",
            "anyo": payload.get("anyo") or "",
            "apple": payload.get("apple") or "",
            "artwork": payload.get("artwork") or "",
            "propuestaPor": miembro,
            "votos": {miembro: True},
        })
        print(f"Propuesta: {nombre} (de {miembro})")

    elif accion == "votar":
        clave = normalizar(payload.get("candidato") or "")
        cand = next((c for c in extra["candidatas"] if normalizar(nombre_candidata(c)) == clave), None)
        if cand is None:
            sys.exit(f"Candidata no encontrada: {payload.get('candidato')!r}")
        cand.setdefault("votos", {})
        cand["votos"][miembro] = bool(payload.get("valor"))
        print(f"Voto de {miembro} en {nombre_candidata(cand)}: {cand['votos'][miembro]}")

    elif accion == "votar_nevera":
        # "tema" ya viene normalizado por la app (mismo formato que usa como
        # clave de EXTRA.overrides) — no se re-normaliza, o dejaría de
        # coincidir con la entrada que lee/escribe el propio index.html.
        tema = payload.get("tema") or ""
        if not tema:
            sys.exit("Falta el tema")
        entry = extra["overrides"].setdefault(tema, {})
        votos = entry.setdefault("votosNevera", {})
        votos[miembro] = bool(payload.get("valor"))
        n_favor = sum(1 for v in votos.values() if v)
        if n_favor >= 4:
            entry["estado"] = "nevera"
            entry["votosNevera"] = {}
        print(f"Voto nevera de {miembro} en {tema}: {n_favor} a favor" + (" -> NEVERA" if n_favor >= 4 else ""))

    else:
        sys.exit(f"Acción desconocida: {accion!r}")

    with open(RUTA_EXTRA, "w", encoding="utf-8") as f:
        json.dump(extra, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
