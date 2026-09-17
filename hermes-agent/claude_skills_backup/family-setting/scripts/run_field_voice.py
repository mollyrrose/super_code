"""Kereszt-modell mezo-hang a /family-setting mezo-panel modhoz.

Egy MASIK gyarto modelljet kerdezi meg ugyanarrol a tablorol, amit a
Claude-lencsek olvasnak. Ez az egyetlen pont az ulesben, ahol nem Claude nez
Claude-ra.

MELYIK MASIK GYARTO -- ez a hoszt-CLI-tol fugg, sosem a sajattol:
  hoszt Claude Code  -> probalt sorrend: deepseek, openai (chatgpt)
  hoszt Codex        -> probalt sorrend: claude, deepseek
A hoszt-felismeres a CLAUDECODE env-valtozora tamaszkodik (ugyanaz a jel,
amit a repo tobbi helye -- pl. last30days/scripts/lib/doctor.py -- mar
hasznal Claude Code azonositasara): ha be van allitva, a hoszt "claude",
kulonben "codex". Ez a repoban jelenleg csak ezt a ket hosztot kulonbozteti
meg -- ha mas CLI-bol (Cursor, Gemini CLI, nyers shell) futtatod, allitsd be
kezzel a FAMILY_SETTING_HOST kornyezeti valtozot ("claude" vagy "codex"),
kulonben tevesen Codex-nek fog latszani.

Hasznalat (a vezeto futtatja, koronkent legfeljebb egyszer):

    python run_field_voice.py --allapot allapot.txt --elhangzott sorok.txt

vagy stdin-en egy JSON-nal:

    {"allapot": "...", "elhangzott": "...", "kerdes": "..."}

Kimenet: sima szoveg a stdout-on (a modell olvasata), plusz egy fejlec, hogy
melyik szolgaltato es melyik modell szolalt meg.

HIBAKEZELESI SZERZODES: ez a script SOHA nem dobhat tracebacket. Barmilyen
hiba eseten exit 2 es egy egysoros uzenet a stderr-en; ilyenkor az ules MEGY
TOVABB, de a vezeto kimondja, hogy ebben a korben nem volt kulso hang.
Az ures tetellista NEM hiba: az azt jelenti, hogy a kulso hang nyugodtnak
latja a kepet -- ez ugyanolyan ervenyes olvasat, mint barmi mas.
A jeloltlistat SORBAN probalja: az elso, amelyik ervenyes valasszal ter
vissza, nyer -- ha az egyik szolgaltato kulcsa hianyzik vagy kimerult, a
kovetkezo jelolt lep be, es csak akkor nemul el a lencse, ha MINDEGYIK
jelolt elbukott.

ADATVEDELMI SZABALY: ez a script CSAK a tablot es az elhangzott mondatokat
kuldi el. A kliens tortenetet, az intake-valaszokat es minden azonosito adatot
NEM. A tabloban a kepviselok szerepnevvel szerepelnek ("apa", "a felelem"),
nem valodi nevekkel -- a vezeto feladata, hogy igy adja at. A script ezt nem
tudja kikenyszeriteni, csak azt garantalja, hogy sajat maga nem olvas be mas
forrast.
"""
import argparse
import io
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path.home() / ".claude" / "skills" / "qPlan" / "scripts"
PROVIDER_SCRIPTS = {
    "openai": SCRIPTS_DIR / "openai_critic.py",
    "deepseek": SCRIPTS_DIR / "deepseek_critic.py",
    "claude": SCRIPTS_DIR / "claude_critic.py",
}

# Host -> ordered list of OTHER-company providers to try. Never includes the
# host's own company, mert az celkeresztbe venne sajat magat, nem egy masik
# gyartot -- lasd a modul docstringjet a hoszt-felismeresrol.
HOST_PROVIDERS = {
    "claude": ["deepseek", "openai"],
    "codex": ["claude", "deepseek"],
}

# A bongeszos tartalek ag szandekosan tiltva van (lasd main()), ezert nem kell
# a ~240s-os bongeszo-varakozasra tartalekolni. Egy ules kozbeni hivas nem
# blokkolhat perceken at: a vezetonek azonnal reagalnia kell tudni.
TIMEOUT_S = 120

PROMPT = """Egy szimbolikus, terbeli kepet kapsz: emberek es fogalmak allnak
egy terben, mindegyiknek van helye, testiranya, tekintete es tartasa. Ez egy
csaladallitas-szimulacio tabloja. NEM ismered a hatterul szolgalo tortenetet,
es nem is kell ismerned.

A feladatod EGY dolog: mondd el, mit latsz a KEPEN. Nem ertelmezed a csaladot,
nem adsz tanacsot, nem talalsz ki hatteret. A terbeli viszonyokrol beszelj:
- ki all kozel, ki tavol, es kihez kepest
- ki nez kire, ki nem nez senkire, ki takarja el kinek a kilatasat
- hol van ures hely, ami feltuno
- kinek a testiranya es a tekintete mond mast (fej ide, torzs oda)
- mi az, ami a kepben nem stimmel, vagy epp mi az, ami mar rendezodott

Ha valami hianyzik a kepbol — egy szerep, egy irany, egy hely —, mondd ki,
mi az. Ha a kep nyugodtnak latszik, azt is mondd ki; nem kell problemat
talalnod.

FORMA: minden eszrevetelt kulon tetelkent adj vissza, magyarul, egyszeruen,
szakszo nelkul. Legfeljebb 8 tetel."""

# A fenti PROMPT onmagaban NEM eleg: a hivott critic-scriptek (qPlan-bol
# ujrahasznositva) egy sajat, bedrotozott rendszerpromptot kuldenek system
# uzenetkent, ami a plan-review JSON alakot kenyszeriti ki -- ha a PROMPT
# csak a "task" mezobe kerulne adatkent, a modell a bedrotozott instrukciot
# koveti, nem ezt. Ezert ezt a teljes szoveget adjuk at system_prompt-kent
# (lasd openai_critic.py / deepseek_critic.py / claude_critic.py
# system_prompt override-jat), kiegeszitve a szallitasi JSON-alak leirasaval,
# amit a lenti kod mar tud ertelmezni.
SYSTEM_PROMPT = PROMPT + """

VALASZOD FORMAJA -- kizarolag ez a JSON, semmi mas elotte vagy utana:
{
  "verdict": "ok",
  "suggestions": [
    { "text": "<egy eszrevetel magyarul>" }
  ]
}
Legfeljebb 8 tetel a "suggestions" listaban. Ha a kep nyugodtnak latszik es
nincs kulon eszrevetel, a "suggestions" lista legyen ures — ez ervenyes
valasz, nem hiba. A "verdict" mezo erteke mindig "ok" legyen, fuggetlenul
attol, hany tetel van."""


def fail(msg):
    """Egysoros hibauzenet a stderr-en, exit 2. Soha nem traceback."""
    sys.stderr.write("run_field_voice: %s\n" % msg)
    return 2


def read_text(path, what):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return fh.read(), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, "%s nem olvashato (%s)" % (what, exc.__class__.__name__)


def detect_host():
    """A hoszt CLI: "claude" vagy "codex". Lasd a modul docstringjet."""
    override = os.environ.get("FAMILY_SETTING_HOST", "").strip().lower()
    if override in HOST_PROVIDERS:
        return override
    return "claude" if os.environ.get("CLAUDECODE") else "codex"


def gather():
    """Visszaad (allapot, elhangzott, kerdes) vagy (None, None, hibauzenet)."""
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--allapot", help="fajl az ALLAPOT-blokkal")
    ap.add_argument("--elhangzott", help="fajl az elhangzott mondatokkal")
    ap.add_argument("--kerdes", default="", help="opcionalis kerdes a vezetotol")
    try:
        args = ap.parse_args()
    except SystemExit:
        return None, None, "rossz parancssori argumentumok"

    if args.allapot:
        allapot, err = read_text(args.allapot, "allapot-fajl")
        if err:
            return None, None, err
        elhangzott = ""
        if args.elhangzott:
            elhangzott, err = read_text(args.elhangzott, "elhangzott-fajl")
            if err:
                return None, None, err
        return (allapot, elhangzott, args.kerdes), None, None

    # stdin JSON ag — explicit utf-8 dekodolas, nem a platform alapertelmezese
    try:
        raw = sys.stdin.buffer.read().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None, None, "a stdin nem utf-8"
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return None, None, "a stdin nem ervenyes JSON"
    if not isinstance(data, dict):
        return None, None, "a stdin JSON nem objektum"
    return (
        data.get("allapot", "") or "",
        data.get("elhangzott", "") or "",
        data.get("kerdes", "") or "",
    ), None, None


def _call_provider(provider, payload, env):
    """Egy jelolt szolgaltatot hiv. Visszaad (verdict_dict, None) sikernel,
    vagy (None, hibauzenet) barmilyen bukasnal -- SOHA nem dob."""
    script = PROVIDER_SCRIPTS[provider]
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True, timeout=TIMEOUT_S, env=env,
        )
    except subprocess.TimeoutExpired:
        return None, "%s: nem valaszolt idoben" % provider
    except Exception as exc:  # noqa: BLE001 - a nemitas a cel, nem a diagnozis
        return None, "%s: nem elerheto (%s)" % (provider, exc.__class__.__name__)

    child_err = proc.stderr.decode("utf-8", errors="replace").strip()
    tail = (" | " + child_err.splitlines()[-1][:160]) if child_err else ""

    if proc.returncode != 0 or not proc.stdout.strip():
        return None, "%s: nem szolalt meg%s" % (provider, tail)

    try:
        verdict = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        if not isinstance(verdict, dict):
            raise ValueError("nem objektum")
    except Exception:
        return None, "%s: ertelmezhetetlen valasz%s" % (provider, tail)

    # A sikeresseg jele a verdict mezo megletе, NEM az, hogy van-e tetel.
    # Az ures tetellista ervenyes valasz: azt jelenti, hogy a kulso hang
    # nyugodtnak latja a kepet — ez ugyanolyan informacio, mint barmi mas.
    if "verdict" not in verdict:
        return None, "%s: hianyos valasz%s" % (provider, tail)

    verdict.setdefault("provider", provider)
    return verdict, None


def main():
    # Backstop: ha barmelyik uzenetbe valaha ekezet kerul, ne dolljon el rajta.
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parts, _unused, err = gather()
    if err:
        return fail(err)
    allapot, elhangzott, kerdes = parts

    if not allapot.strip():
        return fail("ures tablo, nincs mit kerdezni")

    plan = "\n\n".join(filter(None, [
        "=== A TABLO ===",
        allapot,
        "=== AMI ELHANGZOTT ===" if elhangzott.strip() else "",
        elhangzott,
        ("=== A VEZETO KERDESE ===\n" + kerdes) if kerdes.strip() else "",
    ]))

    host = detect_host()
    candidates = HOST_PROVIDERS[host]

    # backend="api" + a bongeszos tartalek KIKAPCSOLVA (csak az openai jelolt
    # olvassa): a hivo scriptnek nincs joga a felhasznalo szemelyes,
    # bejelentkezett ChatGPT-fiokjaba irni az ules tartalmat. Ha az API-keret
    # kimerul, az a jelolt nemuljon el -- ez a dokumentalt biztonsagos
    # degradacio -- ahelyett, hogy a tablo es az elhangzott mondatok a
    # szemelyes beszelgetes-elozmenybe kerulnenek. A tobbi jelolt ettol meg
    # probalkozhat.
    payload = {
        "task": "",
        "plan": plan,
        "ledger": [],
        "backend": "api",
        "system_prompt": SYSTEM_PROMPT,
    }
    env = dict(os.environ, PYTHONIOENCODING="utf-8",
               QPLAN_OPENAI_NO_BROWSER_FALLBACK="1")

    errors = []
    verdict = None
    for provider in candidates:
        verdict, err = _call_provider(provider, payload, env)
        if verdict is not None:
            break
        errors.append(err)

    if verdict is None:
        return fail(
            "a kulso hang egyik jelolt szolgaltatonal sem valaszolt (hoszt: "
            "%s) -- %s" % (host, " | ".join(errors))
        )

    lines = [s.get("text", "") for s in verdict.get("suggestions", [])
             if isinstance(s, dict) and s.get("text")]

    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out.write("[kulso hang: %s/%s]\n\n" % (
        verdict.get("provider", "ismeretlen"), verdict.get("model", "ismeretlen")
    ))
    if lines:
        out.write("\n\n".join(lines) + "\n")
    else:
        out.write("A kulso hang nem lat kiemelendot a kepen — nyugodtnak "
                  "latja.\n")
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
