"""firmas.py — la firma del PROPIETARIO sobre cada versión publicada (Ed25519).

Misma idea (y mismo manifiesto) que firmas.py de Bot Lab, en genérico: `base` es la carpeta del
repositorio que se firma o verifica (el launcher, Bot Lab o cualquier otra app).

  clave        <base>/secrets/propietario.key (una línea aleatoria; solo en las máquinas del propietario).
               La clave Ed25519 se DERIVA de ella: semilla = sha256(clave). No hay secreto nuevo que guardar.
  política     <base>/politica.json: propietario_sha256 (hash de la clave) y propietario_ed25519 (pública en hex).
  manifiesto   sha256 de las líneas «blob ruta» (ordenadas) de `git ls-tree -r <rev>` salvo firmas/.
  firma        firmas/vX.Y.Z.json = {version, manifiesto, firma, publica, fecha, ficheros}
               `ficheros` = {ruta: sha del blob}: la lista exacta de lo que forma parte de la versión.
               Lo firmado es «version manifiesto»; como el manifiesto se recalcula a partir de `ficheros`,
               la lista queda cubierta por la firma.

verificar(rev, publica, base)            con git: ¿esa revisión lleva una firma válida del propietario?
verificar_disco(base, version, publica)  sin git: ¿los ficheros de esa carpeta (un ZIP descargado, una copia
                                         instalada) son EXACTAMENTE los firmados? Calcula el sha de blob en
                                         Python puro: sha1(b"blob %d\\0" % len + contenido).

cryptography es opcional: sin ella firmar y verificar fallan con un mensaje claro.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

from . import RAIZ

CARPETA = "firmas"
RUTA_CLAVE = "secrets/propietario.key"
NO_CODIGO = ()   # nada se excluye del manifiesto salvo firmas/ (igual que Bot Lab)


def disponible() -> bool:
    try:
        import cryptography  # noqa: F401
        return True
    except ImportError:
        return False


def _git(*args, base) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", *args], cwd=str(base), capture_output=True, text=True, errors="replace", timeout=60,
                              stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(args, 127, "", str(e))


# --------------------------------------------------------------------------- claves y política
def ruta_clave(base=None) -> Path:
    return Path(base or RAIZ) / RUTA_CLAVE


def _semilla(ruta: Path) -> bytes:
    clave = Path(ruta).read_text(encoding="utf-8").strip()
    if not clave:
        raise ValueError("clave del propietario vacía")
    return hashlib.sha256(clave.encode("utf-8")).digest()


def sha256_clave(ruta: Path) -> str:
    """El hash que va en politica.json (propietario_sha256)."""
    return _semilla(ruta).hex()


def clave_privada(ruta: Path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    return Ed25519PrivateKey.from_private_bytes(_semilla(ruta))


def publica_hex(ruta: Path) -> str:
    from cryptography.hazmat.primitives import serialization
    pub = clave_privada(ruta).public_key()
    return pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def politica(base=None) -> dict:
    try:
        d = json.loads((Path(base or RAIZ) / "politica.json").read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def publica_conocida(base=None) -> str | None:
    """La clave pública del propietario que esta copia YA conoce: la derivada de su propia clave si es el
    propietario; si no, la de politica.json local (nunca la de un fichero recién descargado)."""
    base = Path(base or RAIZ)
    rc = ruta_clave(base)
    if rc.exists() and disponible():
        try:
            return publica_hex(rc)
        except (OSError, ValueError):
            pass
    p = politica(base).get("propietario_ed25519")
    return str(p) if p else None


# --------------------------------------------------------------------------- manifiesto
def ficheros(rev: str = "HEAD", base=None) -> dict[str, str]:
    """{ruta: sha del blob} de todos los ficheros de la revisión, salvo firmas/."""
    r = _git("ls-tree", "-r", rev, base=base or RAIZ)
    if r.returncode:
        raise RuntimeError("no pude listar el árbol de " + rev + ": " + (r.stderr or r.stdout).strip()[-200:])
    out = {}
    for linea in r.stdout.splitlines():
        meta, _, ruta = linea.partition("\t")
        partes = meta.split()
        if len(partes) < 3 or partes[1] != "blob" or ruta.startswith(CARPETA + "/"):
            continue
        out[ruta] = partes[2]
    return out


def manifiesto_de(lista: dict[str, str]) -> str:
    return hashlib.sha256("\n".join(sorted(f"{sha} {ruta}" for ruta, sha in lista.items())).encode("utf-8")).hexdigest()


def manifiesto(rev: str = "HEAD", base=None) -> str:
    return manifiesto_de(ficheros(rev, base))


def sha_blob(ruta: Path) -> str:
    """El sha1 que git da a un fichero, sin git."""
    ruta = Path(ruta)
    datos = ruta.readlink().as_posix().encode("utf-8") if ruta.is_symlink() else ruta.read_bytes()
    h = hashlib.sha1(b"blob %d\0" % len(datos))
    h.update(datos)
    return h.hexdigest()


# --------------------------------------------------------------------------- firmar
def firmar(version: str, ruta: Path | None = None, rev: str = "HEAD", base=None) -> dict:
    base = Path(base or RAIZ)
    ruta = Path(ruta or ruta_clave(base))
    priv = clave_privada(ruta)
    lista = ficheros(rev, base)
    m = manifiesto_de(lista)
    return {"version": version, "manifiesto": m,
            "firma": priv.sign(f"{version} {m}".encode("utf-8")).hex(),
            "publica": publica_hex(ruta),
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "ficheros": lista}


def escribir_firma(version: str, ruta: Path | None = None, rev: str = "HEAD", base=None) -> Path:
    """firmas/vX.Y.Z.json en la carpeta del repo (luego se añade al commit de la versión)."""
    base = Path(base or RAIZ)
    f = firmar(version, ruta, rev, base)
    destino = base / CARPETA / f"v{version}.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(f, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return destino


def actualizar_politica(ruta: Path | None = None, base=None) -> dict:
    """politica.json con propietario_sha256 y propietario_ed25519 de esta clave (crea el fichero si no existe)."""
    base = Path(base or RAIZ)
    ruta = Path(ruta or ruta_clave(base))
    pol = politica(base)
    pol["propietario_sha256"] = sha256_clave(ruta)
    pol["propietario_ed25519"] = publica_hex(ruta)
    pol.setdefault("nota", "Solo el propietario (quien tiene secrets/propietario.key) firma versiones. "
                           "El launcher solo instala versiones cuya firma verifica con propietario_ed25519.")
    (base / "politica.json").write_text(json.dumps(pol, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return pol


# --------------------------------------------------------------------------- verificar
def _comprobar_firma(f: dict, version: str, publica: str) -> tuple[bool, str]:
    if not disponible():
        return False, "falta la librería cryptography (pip install -r requirements.txt): no se instalan actualizaciones"
    try:
        firma = bytes.fromhex(f["firma"])
        m = str(f["manifiesto"])
        if f.get("version") != version:
            return False, f"la firma es de v{f.get('version')} y no de v{version}"
    except (KeyError, TypeError, ValueError):
        return False, f"firma de v{version} ilegible"
    if f.get("ficheros") is not None:
        if not isinstance(f["ficheros"], dict) or manifiesto_de(f["ficheros"]) != m:
            return False, f"la lista de ficheros de v{version} no corresponde a su manifiesto"
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(str(publica))).verify(firma, f"{version} {m}".encode("utf-8"))
    except (InvalidSignature, ValueError, TypeError):
        return False, f"la firma de v{version} NO es del propietario: no se instala"
    return True, f"firma del propietario válida ({str(f.get('fecha', ''))[:16]})"


def verificar(rev: str, publica: str | None, base=None) -> tuple[bool, str]:
    """Con git: ¿la revisión `rev` (una etiqueta vX.Y.Z) lleva una firma válida del propietario?"""
    base = Path(base or RAIZ)
    if not publica:
        return False, "no conozco la clave pública del propietario (politica.json): no se instala"
    r = _git("show", f"{rev}:VERSION", base=base)
    version = r.stdout.strip() if r.returncode == 0 else ""
    if not version:
        return False, f"{rev}: sin fichero VERSION"
    r = _git("show", f"{rev}:{CARPETA}/v{version}.json", base=base)
    if r.returncode:
        return False, f"v{version} no lleva firma del propietario ({CARPETA}/v{version}.json): no se instala"
    try:
        f = json.loads(r.stdout)
    except ValueError:
        return False, f"firma de v{version} ilegible"
    try:
        m = manifiesto(rev, base)
    except RuntimeError as e:
        return False, str(e)
    if f.get("manifiesto") != m:
        return False, f"la firma de v{version} no corresponde a este código (manifiesto distinto)"
    return _comprobar_firma(f, version, publica)


def verificar_disco(base, version: str, publica: str | None) -> tuple[bool, str, list[str]]:
    """Sin git: ¿los ficheros de `base` son exactamente los firmados en firmas/v<version>.json?
    Devuelve (ok, mensaje, ficheros alterados o ausentes). No mira ficheros de más (datos, logs, venv…)."""
    base = Path(base)
    if not publica:
        return False, "no conozco la clave pública del propietario: no se instala", []
    try:
        f = json.loads((base / CARPETA / f"v{version}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, f"v{version} no lleva firma del propietario ({CARPETA}/v{version}.json)", []
    if not isinstance(f.get("ficheros"), dict):
        return False, f"la firma de v{version} no trae la lista de ficheros (firma antigua): no se puede verificar sin git", []
    ok, msg = _comprobar_firma(f, version, publica)
    if not ok:
        return False, msg, []
    malos = []
    for ruta, sha in sorted(f["ficheros"].items()):
        p = base / ruta
        try:
            if sha_blob(p) != sha:
                malos.append(ruta)
        except OSError:
            malos.append(ruta)
    if malos:
        return False, f"{len(malos)} fichero(s) de v{version} no coinciden con lo firmado", malos
    return True, msg + f" · {len(f['ficheros'])} ficheros verificados", []
