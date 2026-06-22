#!/usr/bin/env bash
# Vollständige Audit-Batterie: Logik + Security + Tests. Exit 0 = alles sauber.
cd "$(dirname "$0")/.." || exit 2
FAIL=0
PY=python3
VPY="tools-venv/bin/python"

step() { printf "  %-42s" "$1"; }
ok()   { echo "✔ $1"; }
bad()  { echo "✖ $1"; FAIL=1; }

echo "──────── AUDIT $(date +%H:%M:%S) ────────"

step "1) Compile (alle Module)"
if $PY -m py_compile apz/*.py panzer.py 2>/tmp/a_compile; then ok OK; else bad "$(cat /tmp/a_compile)"; fi

step "2) Import aller Module"
if NO_COLOR=1 $PY -c "import importlib,pkgutil,apz; [importlib.import_module(f'apz.{m.name}') for m in pkgutil.iter_modules(apz.__path__)]" 2>/tmp/a_imp; then ok OK; else bad "$(cat /tmp/a_imp)"; fi

step "3) pyflakes (Logik/undef. Namen)"
if [ -x "$VPY" ]; then
  OUT=$($VPY -m pyflakes apz/ panzer.py 2>&1); [ -z "$OUT" ] && ok "0 Befunde" || bad "$OUT"
else echo "⚠ venv-pyflakes fehlt (übersprungen)"; fi

step "4) AST: falsche Keyword-Args"
$PY - <<'PYEOF' 2>/tmp/a_kw && ok OK || bad "$(cat /tmp/a_kw)"
import ast,glob,sys
AM={"shell":{"cmd","timeout","root","retries"},"raw":{"args","timeout","check"},
    "getprop":{"key","fresh"},"getprops":{"refresh"}}
prob=[]
for p in glob.glob("apz/*.py")+["panzer.py"]:
    t=ast.parse(open(p,encoding="utf-8").read(),p); sig={}
    for n in ast.walk(t):
        if isinstance(n,ast.FunctionDef):
            a=n.args; sig[n.name]=({x.arg for x in a.posonlyargs+a.args+a.kwonlyargs}, a.kwarg is not None)
    for n in ast.walk(t):
        if not isinstance(n,ast.Call): continue
        kw=[k.arg for k in n.keywords if k.arg]
        if isinstance(n.func,ast.Attribute) and n.func.attr in AM:
            b=[k for k in kw if k not in AM[n.func.attr]]
            if b: prob.append(f"{p}:{n.lineno} .{n.func.attr}() {b}")
        elif isinstance(n.func,ast.Name) and n.func.id in sig and not sig[n.func.id][1]:
            b=[k for k in kw if k not in sig[n.func.id][0]]
            if b: prob.append(f"{p}:{n.lineno} {n.func.id}() {b}")
sys.exit("\n".join(prob)) if prob else None
PYEOF

step "5) SECURITY: keine shell=True/os.system/eval/exec"
# Python eval/exec als Aufruf (nicht .exec von JS in frida_scripts.py), plus shell=True/os.system
{ grep -rnE "shell=True|os\.system|os\.popen" apz/*.py
  grep -rnE "(^|[^.0-9A-Za-z_])(eval|exec)[[:space:]]*\(" apz/*.py | grep -v "apz/frida_scripts.py"
} >/tmp/a_dang 2>/dev/null
if [ -s /tmp/a_dang ]; then bad "$(cat /tmp/a_dang)"; else ok keine; fi

step "6) SECURITY: kein roher Archiv-extract"
# jeder .extract( muss über util.safe_extract_member laufen (util.py selbst = die Implementierung)
if grep -rnE "\.extract(all)?\(" apz/*.py | grep -v "safe_extract_member" | grep -v "apz/util.py:" >/tmp/a_ex 2>&1; then bad "roh: $(cat /tmp/a_ex)"; else ok "nur safe_extract_member"; fi

step "7) SECURITY: keine http://-Downloads"
if grep -rnE "urlretrieve\(\"http://|urlopen\(\"http://|Request\(\"http://" apz/*.py >/tmp/a_http 2>&1; then bad "$(cat /tmp/a_http)"; else ok "nur HTTPS"; fi

step "8) Unit-Tests (-W error, Injection-Guard)"
if $PY -m pytest -q -W error >/tmp/a_pt 2>&1; then ok "$(grep -oE '[0-9]+ passed' /tmp/a_pt | tail -1)"; else bad "$(tail -8 /tmp/a_pt)"; fi

# Aufräumen evtl. erzeugter Arbeitsverzeichnisse
rm -rf forensik_full diagnostics apkscan reports logs out 2>/dev/null

echo "──────────────────────────────────────────"
[ $FAIL -eq 0 ] && echo "✅ AUDIT SAUBER" || echo "❌ AUDIT-BEFUNDE"
exit $FAIL
