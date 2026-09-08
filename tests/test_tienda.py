"""Tests del motor del launcher (agcore.tienda) con un «so» falso: nada toca el sistema real."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

TOKEN_CODIGO = "github_pat_CODIGO_1234567890abcdef"
TOKEN_BUZON = "github_pat_BUZON_abcdef1234567890"


class SoFalso:
    """Registra lo que el launcher pide al sistema y simula git clone creando la carpeta de Bot Lab."""
    ES_WIN = False
    ES_MAC = True
    LAUNCH_AGENTS = None

    def __init__(self, tmp: Path, con_git=True, win=False):
        self.tmp, self.con_git = tmp, con_git
        self.ES_WIN, self.ES_MAC = win, not win
        self.LAUNCH_AGENTS = tmp / "LaunchAgents"
        self.llamadas: list[list[str]] = []
        self.servicios: dict[str, list] = {}
        self.accesos: set = set()
        self.fallos: set = set()          # comandos (por su primera palabra clave) que deben fallar

    # procesos
    def sh(self, *args, cwd=None, timeout=600, env=None, utf8=False):
        a = [str(x) for x in args]
        self.llamadas.append(a)
        texto = " ".join(a)
        if "clone" in a:
            destino = Path(a[-1])
            destino.mkdir(parents=True)
            (destino / "VERSION").write_text("3.16.4\n")
            (destino / "requirements.txt").write_text("numpy\n")
            (destino / "conexion.py").write_text("print('ok')\n")
            (destino / "puente_git.py").write_text("print('{}')\n")
            (destino / "instalar_mac.sh").write_text("#!/bin/zsh\necho instalado\n")
            w = destino / "windows"; w.mkdir()
            for f in ("pasada.bat", "vigilante.bat", "actualizar.bat", "panel.bat"):
                (w / f).write_text("@echo off\n")
            return subprocess.CompletedProcess(a, 0, f"Cloning into '{destino.name}'…\nfrom {a[-2]}\n", "")
        if "venv" in a and "-m" in a:
            carpeta = Path(a[-1])
            (carpeta / ("Scripts" if self.ES_WIN else "bin")).mkdir(parents=True, exist_ok=True)
            (carpeta / ("Scripts" if self.ES_WIN else "bin") / ("python.exe" if self.ES_WIN else "python")).write_text("")
            return subprocess.CompletedProcess(a, 0, "", "")
        if "conexion.py" in a and "conexion" in self.fallos:
            return subprocess.CompletedProcess(a, 1, "", "ERROR: claves incorrectas")
        if "merge-base" in a:
            return subprocess.CompletedProcess(a, 0 if "ancestro" not in self.fallos else 1, "", "")
        if "remote" in a and "get-url" in a:
            return subprocess.CompletedProcess(a, 0, f"https://x-access-token:{TOKEN_CODIGO}@github.com/alejandroogomezzcabrera-collab/ag-launcher.git\n", "")
        if "tag" in a and "-l" in a:
            return subprocess.CompletedProcess(a, 0, "v1.0.0\nv9.9.9\nbasura\n", "")
        if "--estado" in a:
            return subprocess.CompletedProcess(a, 0, json.dumps({"flota": {"nombre": "Flota de Ana", "buzon": True}, "actualizar": "puente al día"}), "")
        if "--sincronizar" in a:
            return subprocess.CompletedProcess(a, 0, f"sincronizado con https://x-access-token:{TOKEN_BUZON}@github.com/x/buzon.git\n", "")
        return subprocess.CompletedProcess(a, 0, f"hecho: {texto}\n", "")

    def suelto(self, args, cwd=None, env=None):
        self.llamadas.append(["suelto", *map(str, args)])
        return True

    def vivo(self, puerto):
        return False

    def git(self):
        return "/usr/bin/git" if self.con_git else None

    def python_sistema(self):
        return sys.executable

    def python_de(self, venv):
        v = Path(venv)
        return v / "Scripts" / "python.exe" if self.ES_WIN else v / "bin" / "python"

    def pythonw_de(self, venv):
        return self.python_de(venv)

    def crear_venv(self, carpeta, nombre):
        return self.sh(sys.executable, "-m", "venv", Path(carpeta) / nombre)

    # servicios
    def _uid(self):
        return 501

    def servicio_cargado(self, label):
        return label in self.servicios

    def instalar_servicio(self, label, programa, carpeta, cada_minutos=None, al_iniciar_sesion=False, keepalive=False, log=print):
        self.servicios[label] = [str(x) for x in programa]
        return True

    def quitar_servicio(self, label):
        self.servicios.pop(label, None)

    def reiniciar_servicio(self, label, carpeta=None):
        return label in self.servicios

    def puede_relanzar(self, label, carpeta=None):
        return label in self.servicios

    def programa_guardado(self, label, carpeta=None):
        p = self.servicios.get(label)
        return {"programa": p, "cwd": str(carpeta or "")} if p else None

    def matar_puerto(self, puerto):
        pass

    # abrir / accesos
    def abrir(self, objetivo):
        self.llamadas.append(["abrir", str(objetivo)])
        return True

    def abrir_carpeta(self, ruta):
        return self.abrir(ruta)

    def ruta_acceso(self, app):
        return self.tmp / "Aplicaciones" / f"{app['nombre']}.app"

    def construir_acceso(self, app, carpeta, log=print):
        p = self.ruta_acceso(app)
        p.mkdir(parents=True, exist_ok=True)
        self.accesos.add(app["id"])
        log(f"✓ {p}")
        return True

    def quitar_acceso(self, app, log=print):
        p = self.ruta_acceso(app)
        if p.exists():
            p.rmdir()
        self.accesos.discard(app["id"])

    def relanzarme(self, *a, **k):
        self.llamadas.append(["relanzarme"])


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    """Un launcher en modo amigo (sin secrets/propietario.key), con datos e invitación en tmp_path."""
    monkeypatch.setenv("AG_DATOS", str(tmp_path / "datos"))
    monkeypatch.setenv("AG_APPS", str(tmp_path / "apps"))
    monkeypatch.setenv("AG_SIN_EXTERNAS", "1")
    import agcore
    from agcore import tienda, invitacion, firmas
    raiz = tmp_path / "launcher"
    raiz.mkdir()
    (raiz / "VERSION").write_text("1.1.0\n")
    (raiz / "catalogo.json").write_text((RAIZ / "catalogo.json").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(agcore, "RAIZ", raiz)
    monkeypatch.setattr(tienda, "RAIZ", raiz)
    monkeypatch.setattr(firmas, "RAIZ", raiz)
    so = SoFalso(tmp_path)
    monkeypatch.setattr(tienda, "SO", so)
    tienda.invalidar()
    tienda._remoto_cache.clear()
    codigo = invitacion.generar("Ana", TOKEN_CODIGO, TOKEN_BUZON)
    return {"tienda": tienda, "so": so, "raiz": raiz, "codigo": codigo, "invitacion": invitacion, "tmp": tmp_path}


def _log():
    lineas = []
    return lineas, lineas.append


def test_modo_amigo_solo_apps_publicas(mundo):
    t = mundo["tienda"]
    assert t.modo() == "amigo"
    ids = [a["id"] for a in t.apps_visibles()]
    assert "bot-lab" in ids and "ag-launcher" in ids and "llm-lab" not in ids
    e = {a["id"]: a for a in t.estado()}
    assert e["bot-lab"]["existe"] is False and e["bot-lab"]["privado"] is True and e["bot-lab"]["instalada"] is False
    assert e["ag-launcher"]["existe"] is True and e["ag-launcher"]["propia"] is True
    assert e["bot-lab"]["carpeta"].endswith("apps/bot-lab") or "apps" in e["bot-lab"]["carpeta"]
    (mundo["raiz"] / "secrets").mkdir(); (mundo["raiz"] / "secrets" / "propietario.key").write_text("clave\n")
    assert t.modo() == "propietario" and "llm-lab" in [a["id"] for a in t.apps_visibles()]


def test_instalar_bot_lab_pide_invitacion(mundo):
    t = mundo["tienda"]
    lineas, log = _log()
    a = t.app("bot-lab")
    ok = t.instalar(a, log, {"alpaca_key": "PKTESTTEST123", "alpaca_secret": "SECRETSECRET123", "acepta_ficticio": True})
    assert ok is False and any("invitación" in l for l in lineas)
    assert not any("clone" in c for c in mundo["so"].llamadas)


def test_instalar_bot_lab_modo_amigo_mac(mundo):
    t, so, inv = mundo["tienda"], mundo["so"], mundo["invitacion"]
    inv.guardar(mundo["codigo"])
    a = t.app("bot-lab")
    lineas, log = _log()
    ok = t.instalar(a, log, {"alpaca_key": "PKTESTTEST123", "alpaca_secret": "SECRETSECRET123", "flota": "Flota de Ana", "acepta_ficticio": True})
    assert ok, "\n".join(lineas)
    carpeta = mundo["tmp"] / "apps" / "bot-lab"
    # ficheros de la receta
    assert (carpeta / ".env").read_text() == "ALPACA_API_KEY=PKTESTTEST123\nALPACA_SECRET_KEY=SECRETSECRET123\nALPACA_BASE_URL=https://paper-api.alpaca.markets\n"
    assert json.loads((carpeta / "buzon.json").read_text()) == {"buzon": f"https://x-access-token:{TOKEN_BUZON}@github.com/alejandroogomezzcabrera-collab/bot_lab-buzon.git"}
    assert json.loads((carpeta / "flota.json").read_text()) == {"auto_codigo": True, "compartir": True, "nombre": "Flota de Ana", "instalada_por": "launcher"}
    assert all((carpeta / d).is_dir() for d in ("logs", "backups", "prodigios"))
    # clon con token en la URL, depth 50, autocrlf false; venv «venv» (no .venv); conexion.py; instalador mac
    clon = next(c for c in so.llamadas if "clone" in c)
    assert f"https://x-access-token:{TOKEN_CODIGO}@github.com/alejandroogomezzcabrera-collab/bot_lab.git" in clon and "--depth" in clon and "core.autocrlf=false" in clon
    assert (carpeta / "venv" / "bin" / "python").exists() and not (carpeta / ".venv").exists()
    assert any("conexion.py" in c for c in so.llamadas)
    assert any(str(carpeta / "instalar_mac.sh") in c for c in so.llamadas)
    assert "bot-lab" in so.accesos
    # ni las claves ni los tokens aparecen en el registro
    registro = "\n".join(lineas)
    assert "SECRETSECRET123" not in registro and "PKTESTTEST123" not in registro
    assert TOKEN_CODIGO not in registro and TOKEN_BUZON not in registro and "x-access-token:***@" in registro


def test_instalar_bot_lab_windows_crea_las_cuatro_tareas(mundo, monkeypatch):
    t, so, inv = mundo["tienda"], mundo["so"], mundo["invitacion"]
    so.ES_WIN, so.ES_MAC = True, False
    inv.guardar(mundo["codigo"])
    a = t.app("bot-lab")
    lineas, log = _log()
    ok = t.instalar(a, log, {"alpaca_key": "PKTESTTEST123", "alpaca_secret": "SECRETSECRET123", "acepta_ficticio": True})
    assert ok, "\n".join(lineas)
    assert set(so.servicios) == {"BotLab pasada", "BotLab vigilante", "BotLab actualizar", "BotLab panel"}
    assert so.servicios["BotLab pasada"][0].endswith("pasada.bat")
    assert any("puente_git.py" in c and "--sincronizar" in c for c in so.llamadas)
    assert any("panel.bat" in " ".join(c) for c in so.llamadas)
    e = {x["id"]: x for x in t.estado()}["bot-lab"]
    assert e["instalada"] is True and e["extra"] is True and set(e["servicios"]) == set(so.servicios)


def test_instalar_bot_lab_claves_malas(mundo):
    t, so, inv = mundo["tienda"], mundo["so"], mundo["invitacion"]
    inv.guardar(mundo["codigo"])
    so.fallos.add("conexion")
    lineas, log = _log()
    assert t.instalar(t.app("bot-lab"), log, {"alpaca_key": "PKTESTTEST123", "alpaca_secret": "SECRETSECRET123", "acepta_ficticio": True}) is False
    assert any("claves no funcionan" in l for l in lineas)
    assert not so.servicios
    # sin marcar la casilla ni claves no se empieza
    lineas, log = _log()
    assert t.instalar(t.app("bot-lab"), log, {}) is False and any("casilla" in l or "claves" in l for l in lineas)


def test_sincronizar_enmascara_tokens(mundo):
    t, so, inv = mundo["tienda"], mundo["so"], mundo["invitacion"]
    inv.guardar(mundo["codigo"])
    lineas, log = _log()
    t.instalar(t.app("bot-lab"), log, {"alpaca_key": "PKTESTTEST123", "alpaca_secret": "SECRETSECRET123", "acepta_ficticio": True})
    lineas, log = _log()
    assert t.sincronizar(t.app("bot-lab"), log) is True
    registro = "\n".join(lineas)
    assert TOKEN_BUZON not in registro and "x-access-token:***@" in registro and "Flota de Ana" in registro
    # actualizar una app con puente = sincronizar (nunca git pull en su carpeta)
    lineas, log = _log()
    assert t.actualizar(t.app("bot-lab"), log) is True
    assert not any("pull" in c or "merge" in c for c in so.llamadas)


def test_actualizar_launcher_rechaza_etiqueta_no_firmada(mundo):
    t, so, raiz = mundo["tienda"], mundo["so"], mundo["raiz"]
    (raiz / "politica.json").write_text(json.dumps({"propietario_ed25519": "00" * 32}))
    # un repositorio de verdad con la etiqueta v9.9.9 pero SIN firmas/v9.9.9.json (fetch y merge-base los simula el so falso)
    for c in (["init", "-q"], ["-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"],
              ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "v9.9.9"], ["tag", "v9.9.9"]):
        subprocess.run(["git", "-C", str(raiz), *c], check=True, capture_output=True)
    lineas, log = _log()
    ok = t.actualizar(t.app("ag-launcher"), log)
    assert ok is False
    registro = "\n".join(lineas)
    assert "v9.9.9" in registro and "no lleva firma" in registro
    assert not any("merge" in c and "--ff-only" in c for c in so.llamadas)
    assert TOKEN_CODIGO not in registro
    # y si la etiqueta no está en main, tampoco
    so.fallos.add("ancestro")
    lineas, log = _log()
    assert t.actualizar(t.app("ag-launcher"), log) is False and any("rama principal" in l for l in lineas)


def test_actualizar_launcher_remoto_distinto(mundo, monkeypatch):
    t, so, raiz = mundo["tienda"], mundo["so"], mundo["raiz"]
    (raiz / ".git").mkdir()
    orig = so.sh

    def sh(*a, **k):
        if "get-url" in a:
            return subprocess.CompletedProcess(a, 0, "https://github.com/otro/repo.git\n", "")
        return orig(*a, **k)
    so.sh = sh
    lineas, log = _log()
    assert t.actualizar(t.app("ag-launcher"), log) is False and any("no es el repositorio del catálogo" in l for l in lineas)


def test_desinstalar_y_registro(mundo):
    t, so, inv = mundo["tienda"], mundo["so"], mundo["invitacion"]
    inv.guardar(mundo["codigo"])
    lineas, log = _log()
    t.instalar(t.app("bot-lab"), log, {"alpaca_key": "PKTESTTEST123", "alpaca_secret": "SECRETSECRET123", "acepta_ficticio": True})
    carpeta = mundo["tmp"] / "apps" / "bot-lab"
    (carpeta / "logs" / "puente.log").write_text(f"clonado https://x-access-token:{TOKEN_BUZON}@github.com/x/y.git\n")
    assert TOKEN_BUZON not in t.registro(t.app("bot-lab")) and "***" in t.registro(t.app("bot-lab"))
    lineas, log = _log()
    assert t.desinstalar(t.app("bot-lab"), log) is True
    assert not so.servicios and "bot-lab" not in so.accesos
    assert (carpeta / ".env").exists()            # los datos se quedan
    assert t.abrir(t.app("bot-lab")).startswith("abriendo http://localhost:8484")
