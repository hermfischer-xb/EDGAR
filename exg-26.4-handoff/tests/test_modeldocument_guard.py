"""The three modelDocument guards in validate/__init__.py return quietly for an instance that did not load.

A control strips each guard from the same source and must raise the production error, so the test shows
the defect is real rather than assuming it.  Runs without Arelle.
Usage: python3 test_modeldocument_guard.py [path to EDGAR plugin checkout]   (or set EDGAR_PLUGIN)
"""
import ast, os, sys

PLUGIN = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("EDGAR_PLUGIN", ".")
F = os.path.join(PLUGIN, "validate", "__init__.py")
WANT = {"testcaseVariationXbrlLoaded", "testcaseVariationXbrlValidated", "testcaseVariationValidated"}
src = open(F, encoding="utf-8").read()
funcs = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name in WANT]
assert {f.name for f in funcs} == WANT, {f.name for f in funcs}

class Type:  # only the members the guards mention
    INSTANCE, INLINEXBRL, INLINEXBRLDOCUMENTSET = "i", "x", "xs"
def pluginClassMethods(name):
    return iter(())
class Filing:
    def __init__(self, *a, **k): raise AssertionError("reached Filing()")
class Stub:
    def __init__(self, **kw): self.__dict__.update(kw)

def build(source):
    ns = {"Type": Type, "pluginClassMethods": pluginClassMethods, "Filing": Filing}
    exec(compile(ast.Module(body=[ast.parse(source).body[0]], type_ignores=[]), F, "exec"), ns)
    return ns

def instance(modelDocument):
    mm = Stub(validateDisclosureSystem=True, disclosureSystem=Stub(EFMplugin=True), cntlr=Stub())
    mm.efmFiling = Stub(getReport=lambda x: None, options=Stub(), errors=[], reports=[])
    return Stub(modelManager=mm, modelDocument=modelDocument, fileSource=Stub(), errorCaptureLevel=0)

testcase = Stub(efmOptions=Stub())
calls = {"testcaseVariationXbrlLoaded": lambda f, i: f(testcase, i, None),
         "testcaseVariationXbrlValidated": lambda f, i: f(testcase, i),
         "testcaseVariationValidated": lambda f, i: f(testcase, i)}

ok = True
for node in funcs:
    source = ast.get_source_segment(src, node)
    try:
        calls[node.name](build(source)[node.name], instance(None))
        print(f"PASS {node.name}: returns quietly when modelDocument is None")
    except Exception as e:
        ok = False
        print(f"FAIL {node.name}: {type(e).__name__}: {e}")
    stripped = "\n".join(l for l in source.splitlines() if "modelDocument and" not in l)
    try:
        calls[node.name](build(stripped)[node.name], instance(None))
        ok = False
        print(f"FAIL {node.name}: control without the guard did not raise, so this test proves nothing")
    except AttributeError as e:
        print(f"     control without the guard raises AttributeError: {e}")

# the guard must not suppress the normal path: with a loaded document the body is entered
loaded = [n for n in funcs if n.name == "testcaseVariationXbrlLoaded"][0]
try:
    build(ast.get_source_segment(src, loaded))["testcaseVariationXbrlLoaded"](
        testcase, instance(Stub(type=Type.INSTANCE, uri="x.htm")), None)
    ok = False
    print("FAIL loaded instance: body not entered")
except Exception as e:  # any failure from deeper in the body (unstubbed globals) shows execution got through
    print(f"PASS loaded instance still enters the body (reached {type(e).__name__} deeper in)")
print("ALL PASS" if ok else "FAILURES")
sys.exit(0 if ok else 1)
