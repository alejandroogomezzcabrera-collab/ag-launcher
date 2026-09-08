"""Tests del código de invitación (agcore.invitacion)."""
import json
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


@pytest.fixture
def inv(tmp_path, monkeypatch):
    monkeypatch.setenv("AG_DATOS", str(tmp_path / "datos"))
    from agcore import invitacion
    return invitacion


def test_generar_y_validar(inv):
    codigo = inv.generar("Ana López", "github_pat_AAAA1111bbbb2222", "github_pat_CCCC3333dddd4444")
    assert codigo.isascii() and "=" not in codigo and "+" not in codigo and "/" not in codigo
    d = inv.validar(codigo)
    assert d["v"] == 1 and d["amigo"] == "Ana López" and d["codigo"] == "github_pat_AAAA1111bbbb2222" and d["buzon"] == "github_pat_CCCC3333dddd4444"
    assert d["creada"][:2] == "20"
    assert inv.validar("  " + codigo + "\n") == d                  # espacios y saltos alrededor no importan
    assert inv.publica(d) == {"amigo": "Ana López", "creada": d["creada"]}


def test_codigos_malos(inv):
    for malo in ("", "   ", "hola", "eyJ2IjoyfQ", "x" * 5000, None, 12):
        with pytest.raises(inv.ErrorInvitacion):
            inv.validar(malo)
    with pytest.raises(inv.ErrorInvitacion):
        inv.validar(inv.generar_desde({"v": 1, "amigo": "Ana", "codigo": "corto", "buzon": "github_pat_CCCC3333dddd4444"}))
    with pytest.raises(inv.ErrorInvitacion):
        inv.generar("", "github_pat_AAAA1111bbbb2222", "github_pat_CCCC3333dddd4444")
    with pytest.raises(inv.ErrorInvitacion):
        inv.generar("Ana", "con espacios no", "github_pat_CCCC3333dddd4444")


def test_guardar_leer_borrar(inv, tmp_path):
    assert inv.leer() is None
    codigo = inv.generar("Ana", "github_pat_AAAA1111bbbb2222", "github_pat_CCCC3333dddd4444")
    d = inv.guardar(codigo)
    f = tmp_path / "datos" / "invitacion.json"
    assert f.exists() and json.loads(f.read_text())["amigo"] == "Ana"
    if os.name != "nt":
        assert oct(f.stat().st_mode & 0o777) == "0o600"
    assert inv.leer() == d
    inv.borrar()
    assert inv.leer() is None and not f.exists()
    f.write_text("{basura")
    assert inv.leer() is None


def test_urls_y_enmascarado(inv):
    repo = "https://github.com/alejandroogomezzcabrera-collab/bot_lab.git"
    con = inv.url_con_token(repo, "github_pat_AAAA1111bbbb2222")
    assert con == "https://x-access-token:github_pat_AAAA1111bbbb2222@github.com/alejandroogomezzcabrera-collab/bot_lab.git"
    assert inv.sin_token(con) == repo and inv.sin_token(repo) == repo
    texto = f"clonando {con} y token suelto github_pat_AAAA1111bbbb2222 y otro ghp_abc123def456"
    m = inv.enmascarar(texto, ["github_pat_AAAA1111bbbb2222"])
    assert "github_pat_AAAA1111bbbb2222" not in m and "abc123def456" not in m and "x-access-token:***@github.com" in m
    assert inv.enmascarar("sin nada") == "sin nada"
