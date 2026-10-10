# Isolated Chapter 3 one-segment V5 candidate. Do not edit production.
import os, sys, json, hashlib, importlib.util, ctypes, gc
from pathlib import Path
for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[key]="1"
root=Path(r"D:\SAYDI\OWNER_APPROVED_NATURAL_V5\Chuong_03")
out=Path(r"D:\SAYDI\QC_STAGING\CH03_V5_QC02_VOICE_JOIN_145_146")
out.mkdir(parents=True,exist_ok=True)
src=root/"chunks"/"000146.wav"
master=root/"CHUONG_03_OWNER_APPROVED_V5.REVIEW.mp3"
def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
before=(sha(src),sha(master))
def free_gb():
    class M(ctypes.Structure):
        _fields_=[("size",ctypes.c_ulong),("load",ctypes.c_ulong),("total",ctypes.c_ulonglong),("free",ctypes.c_ulonglong),("a",ctypes.c_ulonglong),("b",ctypes.c_ulonglong),("c",ctypes.c_ulonglong),("d",ctypes.c_ulonglong),("e",ctypes.c_ulonglong)]
    x=M();x.size=ctypes.sizeof(x)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(x))
    return x.free/(1024**3)
if free_gb()<1.5:raise RuntimeError("RAM_ADMISSION_BELOW_1P5_GB")
k=ctypes.windll.kernel32
k.GetCurrentProcess.restype=ctypes.c_void_p
k.SetProcessAffinityMask(k.GetCurrentProcess(),1)
k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
m=json.loads((root/"manifest.json").read_text(encoding="utf8"))
item=m["segments"][146]
s=importlib.util.spec_from_file_location("owner_v5",r"C:\SAYDI\narration_director_v1\render_owner_approved_v5.py")
v5=importlib.util.module_from_spec(s);s.loader.exec_module(v5)
assert m["reference_sha256"]==v5.reference_verified()==item["reference_fingerprint"]
dest=out/"000146_candidate_r1.wav"
if dest.exists():raise RuntimeError("CANDIDATE_ALREADY_EXISTS_NO_OVERWRITE")
from vieneu import Vieneu
import soundfile as sf
tts=Vieneu(backend="onnx",precision="fp32")
try:
    tts.add_voice(v5.VOICE,str(v5.REF),denoise=False,save=False,description="Owner-approved V5 native tempo",gender="male")
    audio=tts.infer(item["spoken_text"],voice=v5.VOICE,max_chars=320,temperature=.67,top_k=22,top_p=.90)
    raw=out/"000146_candidate_r1_raw.wav"
    tts.save(audio,str(raw))
finally:
    try:tts.close()
    except Exception:pass
    del tts
    gc.collect()
assert sf.info(str(raw)).duration>1
v5.clean_clip(raw,dest)
if (sha(src),sha(master))!=before:raise RuntimeError("PRODUCTION_SOURCE_MODIFIED")
report={"chapter":3,"segment":146,"status":"CANDIDATE_CREATED_REVIEW_REQUIRED","candidate":str(dest),"candidate_sha256":sha(dest),"source_wav_sha256":before[0],"source_mp3_sha256":before[1],"reference_fingerprint":m["reference_sha256"],"tts_text_sha256":item["tts_text_sha256"],"engine":"VieNeu ONNX V5 fp32","native_tempo":True,"production_modified":False,"owner_approved":False}
(out/"candidate_r1.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps({"status":report["status"],"candidate":str(dest),"seconds":sf.info(str(dest)).duration,"free_ram_gb":round(free_gb(),2)},ensure_ascii=True),flush=True)
