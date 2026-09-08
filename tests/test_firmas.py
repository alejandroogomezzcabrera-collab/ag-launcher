"""Tests de agcore.firmas: firmar/verificar (con git) y verificar_disco (sin git) con una clave temporal."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from agcore import firmas  # noqa: E402

pytestmark = pytest.mark.skipif(not firmas.disponible(), reason="falta cryptography")


def _git(base, *args):
    return subprocess.run(["git", "-C", str(base), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    base = tmp_path / "repo"
    base.mkdir()
    (base / "VERSION").write_text("1.2.3\n")
    (base / "agcore").mkdir()
    (base / "agcore" / "x.py").write_text("print('hola')\n")
    (base / "windows").mkdir()
    (base / "windows" / "a.bat").write_bytes(b"@echo off\r\n")
    (base / "secrets").mkdir()
    (base / "secrets" / "propietario.key").write_text("clave-de-prueba-0123456789\n")
    (base / ".gitignore").write_text("secrets/\n")
    _git(base, "init", "-q")
    _git(base, "add", "-A")
    _git(base, "commit", "-q", "-m", "v1.2.3")
    return base


def test_firmar_y_verificar_con_git(repo):
    clave = repo / "secrets" / "propietario.key"
    f = firmas.firmar("1.2.3", clave, "HEAD", repo)
    assert set(f) == {"version", "manifiesto", "firma", "publica", "fecha", "ficheros"}
    assert set(f["ficheros"]) == {"VERSION", "agcore/x.py", "windows/a.bat", ".gitignore"}
    assert f["manifiesto"] == firmas.manifiesto_de(f["ficheros"]) == firmas.manifiesto("HEAD", repo)
    destino = firmas.escribir_firma("1.2.3", clave, "HEAD", repo)
    assert destino == repo / "firmas" / "v1.2.3.json"
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "firma"); _git(repo, "tag", "v1.2.3")
    pub = firmas.publica_hex(clave)
    ok, msg = firmas.verificar("v1.2.3", pub, repo)
    assert ok, msg
    assert firmas.manifiesto("v1.2.3", repo) == f["manifiesto"]        # firmas/ no entra en el manifiesto
    # otra clave no vale
    otra = repo / "otra.key"; otra.write_text("otra clave\n")
    ok, msg = firmas.verificar("v1.2.3", firmas.publica_hex(otra), repo)
    assert not ok and "NO es del propietario" in msg
    assert firmas.verificar("v1.2.3", None, repo)[0] is False
    # una versión con el código cambiado y la firma vieja
    (repo / "agcore" / "x.py").write_text("print('malicioso')\n"); (repo / "VERSION").write_text("1.2.4\n")
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "v1.2.4 sin firma"); _git(repo, "tag", "v1.2.4")
    ok, msg = firmas.verificar("v1.2.4", pub, repo)
    assert not ok and "no lleva firma" in msg
    shutil.copy(repo / "firmas" / "v1.2.3.json", repo / "firmas" / "v1.2.4.json")
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "firma copiada"); _git(repo, "tag", "-f", "v1.2.4")
    ok, msg = firmas.verificar("v1.2.4", pub, repo)
    assert not ok and "no corresponde" in msg
    # política
    pol = firmas.actualizar_politica(clave, repo)
    assert pol["propietario_ed25519"] == pub and len(pol["propietario_sha256"]) == 64
    assert firmas.publica_conocida(repo) == pub
    (repo / "secrets" / "propietario.key").unlink()
    assert firmas.publica_conocida(repo) == pub                        # sin clave: la de politica.json


def test_sha_blob_como_git(repo):
    for ruta in ("VERSION", "agcore/x.py", "windows/a.bat"):
        assert firmas.sha_blob(repo / ruta) == _git(repo, "rev-parse", f"HEAD:{ruta}").strip()


def test_verificar_disco_sin_git(repo, tmp_path):
    clave = repo / "secrets" / "propietario.key"
    pub = firmas.publica_hex(clave)
    firmas.escribir_firma("1.2.3", clave, "HEAD", repo)
    _git(repo, "add", "-A"); _git(repo, "commit", "-q", "-m", "firma"); _git(repo, "tag", "v1.2.3")
    # «un ZIP descargado»: los ficheros de la etiqueta, sin .git
    zip_ = tmp_path / "descarga"
    shutil.copytree(repo, zip_, ignore=shutil.ignore_patterns(".git", "secrets"))
    ok, msg, malos = firmas.verificar_disco(zip_, "1.2.3", pub)
    assert ok and malos == [] and "4 ficheros" in msg, msg
    # ficheros de más (datos, logs) no molestan
    (zip_ / "logs").mkdir(); (zip_ / "logs" / "x.log").write_text("x")
    assert firmas.verificar_disco(zip_, "1.2.3", pub)[0]
    # un fichero alterado o ausente sí
    (zip_ / "agcore" / "x.py").write_text("print('malicioso')\n")
    ok, msg, malos = firmas.verificar_disco(zip_, "1.2.3", pub)
    assert not ok and malos == ["agcore/x.py"]
    (zip_ / "agcore" / "x.py").unlink()
    assert firmas.verificar_disco(zip_, "1.2.3", pub)[2] == ["agcore/x.py"]
    # la lista de ficheros está cubierta por la firma: si la retocan, no verifica
    f = json.loads((zip_ / "firmas" / "v1.2.3.json").read_text())
    f["ficheros"].pop("agcore/x.py")
    (zip_ / "firmas" / "v1.2.3.json").write_text(json.dumps(f))
    ok, msg, _ = firmas.verificar_disco(zip_, "1.2.3", pub)
    assert not ok and "manifiesto" in msg
    # clave equivocada, versión sin firma
    otra = tmp_path / "otra.key"; otra.write_text("otra\n")
    assert not firmas.verificar_disco(repo, "1.2.3", firmas.publica_hex(otra))[0]
    assert not firmas.verificar_disco(repo, "9.9.9", pub)[0]
