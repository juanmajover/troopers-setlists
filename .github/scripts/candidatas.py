#!/usr/bin/env python3
"""Aplica una acción (proponer/votar/votar_nevera) sobre extra.json.
Ejecutado por el workflow "Candidatas" — es el único código que escribe
en extra.json a partir de lo que dispara cualquiera de los 5 miembros.
"""
import json
import re
import sys
import unicodedata
from urllib.parse import urlparse

MIEMBROS = ["JM", "Edu", "Fer", "Fran", "Rafeta"]
RUTA_EXTRA = "extra.json"


def normalizar(s):
    s = (s or "").strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def nombre_candidata(c):
    return c.get("titulo", "") + (" - " + c["artista"] if c.get("artista") else "")


def texto(payload, campo, limite):
    return str(payload.get(campo) or "").strip()[:limite]


def url_https(payload, campo):
    valor = texto(payload, campo, 1000)
    return valor if urlparse(valor).scheme == "https" else ""


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
        titulo = texto(payload, "titulo", 200).upper()
        artista = texto(payload, "artista", 200)
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
            "afinacion": texto(payload, "afinacion", 40).upper(),
            "comentario": texto(payload, "comentario", 500),
            "dur": int(dur) if isinstance(dur, (int, float)) else None,
            "album": texto(payload, "album", 200),
            "anyo": texto(payload, "anyo", 4) if re.fullmatch(r"\d{4}", texto(payload, "anyo", 4)) else "",
            "apple": url_https(payload, "apple"),
            "artwork": url_https(payload, "artwork"),
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
        tema = texto(payload, "tema", 300)
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

    elif accion == "descartar":
        clave = normalizar(payload.get("candidato") or "")
        cand = next((c for c in extra["candidatas"] if normalizar(nombre_candidata(c)) == clave), None)
        if cand is None:
            sys.exit(f"Candidata no encontrada: {payload.get('candidato')!r}")
        if cand.get("propuestaPor") != miembro:
            sys.exit(f"{miembro} no puede descartar una propuesta de {cand.get('propuestaPor')!r}")
        extra["candidatas"].remove(cand)
        print(f"Descartada: {nombre_candidata(cand)} (por {miembro})")

    elif accion == "editar":
        clave = normalizar(payload.get("candidato") or "")
        cand = next((c for c in extra["candidatas"] if normalizar(nombre_candidata(c)) == clave), None)
        if cand is None:
            sys.exit(f"Candidata no encontrada: {payload.get('candidato')!r}")
        if cand.get("propuestaPor") != miembro:
            sys.exit(f"{miembro} no puede editar una propuesta de {cand.get('propuestaPor')!r}")
        cand["afinacion"] = texto(payload, "afinacion", 40).upper()
        cand["comentario"] = texto(payload, "comentario", 500)
        print(f"Editada: {nombre_candidata(cand)} (por {miembro})")

    else:
        sys.exit(f"Acción desconocida: {accion!r}")

    with open(RUTA_EXTRA, "w", encoding="utf-8") as f:
        json.dump(extra, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
