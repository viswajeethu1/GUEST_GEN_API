#!/usr/bin/env python3
import os
import json
import time
import random
import hashlib
import hmac
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from flask import Flask, request, jsonify
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import the provided proto file
try:
    import PorTs_pb2
except ImportError:
    PorTs_pb2 = None

app = Flask(__name__)
try:
    app.json.ensure_ascii = False
except AttributeError:
    app.config['JSON_AS_ASCII'] = False

# --- CONSTANTS ---
AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])

CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
APP_ID = 100067

OAUTH_REGISTER_URL = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
OAUTH_TOKEN_URL    = "https://100067.connect.garena.com/oauth/guest/token/grant"
MAJOR_REGISTER_URL = "https://loginbp.ppmainecoonghj.com/MajorRegister"
NEWBIE_URL         = "https://loginbp.ppmainecoonghj.com/ChooseNewbieChoice"
MAJOR_LOGIN_URL    = "https://loginbp.ppmainecoonghj.com/MajorLogin"

# Force IND Server for GetLoginData
IND_SERVER_URL = "https://client.ind.freefiremobile.com"

X_GA_SV = "1789636317"
USAGE_PASSWORD = "jeethurviswa"
MAX_COUNT = 8
TIME_BUDGET_SECONDS = 55

REGION_CONFIG = {
    "IND": {"name": "IND", "label": "India", "region": "IND", "lang": "en"},
    "BD":  {"name": "BD", "label": "Bangladesh", "region": "BD", "lang": "bn"},
}

_DESIGNS = [
    '▲','ℳ','☆','°','ℛ','『','ツ','◇','༺','◆','웃','꧁','彡','★','ン',
    '•','乂','༄','유','ヅ','Ø','♪','Ƹ','⌂','シ','⊹','·','∞','♡','✦','✧',
    '◈','►','꧂','༻','ῗ','ʜ','ɪ','ᴋ','ᴍ','ɴ','꧇','꧀','』','「','」','《','》',
    'ッ','ジ','ヅ','乂','ℳ','ℛ','ꧢ','Ƈ','Ƨ','Ƴ','Ɯ','Ƶ','⋆','⋈'
]
_DESIGNS = list(dict.fromkeys(_DESIGNS))

XOR_KEY = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
           0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]

FIELD_22_HEX = (
    "474752450101010062020000a78910bd098e3ff2e4345d59a31db114ea088f37e32e65"
    "212ff96621793d9eb78720d0bf2ac95176569765247ada5eb01376b3b9931794a4946"
    "d76ef8890779f3f2129317e6e1cb2fdcf7b06247cea343b8d4f167eff85a2e1dfe99"
    "b4583a7e1a155dbe7f7f85cff3b223eb77222ec1228f3ee1ef6ce7f8ca24b00a554"
    "e497328812f8df74c82d519ae3e3ceab436eb145e8a517089a7cef6a4efb22214b2"
    "a4b19989b74807584afe5e52825e7ac60e19a596a9bf02d961de6a0ed2515ec6023"
    "fdb7684d9464b97b21c527ce61b6bee4ef30d20a1fa33a996952d44d44e44f2f86c"
    "768aaf2a7808ad60f91048dca0207961ba7c2555c48341b30190debc775edb2cee24"
    "4cf51fca3760ce4388be2db45e80b813b5beb9c784007b7762d7a1e428affc8a3a4"
    "cd76cbaef648a274297fde33233dccd3f272cb77f39a1affe0365a24954111f768f72"
    "0e77535af024bea2b2726c3bac992374755c3deacf09235e6865d456e651680d115a"
    "751a797225eaacdf9a513cf104526e1a32e5296e111a33ae581a63850837921df848"
    "9adfd41ea895b7cf3f5b2e45d538a6e4f032f590ccbb7daf5fa9c50adadee0799661"
    "4c3f957bda349e6c484fdf55970d1943ad7955a76671298b6d98b636b69ebde6bc94"
    "dbd93ac3393a6ae230130445b2d744189167854a5617be2393e7d8fbb5719a1b4754"
    "1ba466167e3e05a6c244f1301ee2035acf94dffc8adbde747d5cd85e35ead3acc372"
    "a59c4220e54bf63f9d80485f3de2518495c1d0f78c911d2da595911fd2a1989cf17"
    "cf3ded5f6c92dea64d675c555c11df92d6c517ca5d0d61a8962f43f76ec7e87596c"
    "8325ebf9ab0f8e6d2eca33c511ceac6980906ebd68c478665591dcecf788ec6ef34c"
    "fbe3fcc279c6147c5bf91cd43cdc9704236"
)

MSDK_USER_AGENTS = [
    "GarenaMSDK/4.0.42(KB2003 ;Android 13;en;HK;app 2.130.1 2019118332;)",
    "GarenaMSDK/4.0.42(SM-G998B ;Android 14;en;IN;app 2.131.0 2019118527;)",
    "GarenaMSDK/4.0.42(CPH2095 ;Android 12;en;ID;app 2.129.1 2019118142;)",
    "GarenaMSDK/4.0.42(Redmi 2404ARN45A ;Android 13;en;IN;app 2.132.0 2019118721;)",
]
UNITY_USER_AGENTS = [
    "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
    "UnityPlayer/2021.3.27f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
]
IP_ADDRESSES = [f"151.158.158.{n}" for n in range(220, 240)]

# --- HELPERS ---
def pick_msdk_ua(): return random.choice(MSDK_USER_AGENTS)
def pick_unity_ua(): return random.choice(UNITY_USER_AGENTS)

def generate_nickname(prefix):
    p = prefix[:7] if prefix else "VISWA"
    suffix = ''.join(random.choices(_DESIGNS, k=random.randint(3, 4)))
    return p + suffix

def generate_password():
    return os.urandom(32).hex().upper()

def write_varint(v):
    r = []
    while v > 127: r.append((v & 0x7F) | 0x80); v >>= 7
    r.append(v); return bytes(r)

def write_varint_field(fn, v): return write_varint((fn << 3) | 0) + write_varint(v)
def write_string_field(fn, v):
    b = v.encode("utf-8")
    return write_varint((fn << 3) | 2) + write_varint(len(b)) + b
def write_bytes_field(fn, v):
    return write_varint((fn << 3) | 2) + write_varint(len(v)) + v

def assemble_proto(fields):
    data = bytearray()
    for k, v in fields.items():
        if isinstance(v, int): data.extend(write_varint_field(k, v))
        elif isinstance(v, str): data.extend(write_string_field(k, v))
        elif isinstance(v, (bytes, bytearray)): data.extend(write_bytes_field(k, bytes(v)))
    return bytes(data)

def aes_encrypt(plain):
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(plain, AES.block_size))

def read_varint(data, offset):
    r, s = 0, 0
    while True:
        if offset >= len(data): raise IndexError("eof")
        b = data[offset]; r |= (b & 0x7F) << s; offset += 1
        if not (b & 0x80): break
        s += 7
    return r, offset

def parse_proto(data):
    result, offset = {}, 0
    while offset < len(data):
        try: tag, offset = read_varint(data, offset)
        except Exception: break
        fn, wt = tag >> 3, tag & 0x7
        try:
            if wt == 0:
                v, offset = read_varint(data, offset); result[fn] = v
            elif wt == 2:
                ln, offset = read_varint(data, offset)
                v = data[offset:offset+ln]; offset += ln
                try: result[fn] = v.decode("utf-8")
                except: result[fn] = v.hex()
            elif wt == 1: result[fn] = data[offset:offset+8].hex(); offset += 8
            elif wt == 5: result[fn] = data[offset:offset+4].hex(); offset += 4
            else: break
        except Exception: break
    return result

def xor_open_id(open_id):
    b = open_id.encode("utf-8")
    return bytes(x ^ XOR_KEY[i % len(XOR_KEY)] for i, x in enumerate(b))

def generate_signature(payload):
    body = json.dumps(payload, separators=(",", ":"))
    return hmac.new(CLIENT_SECRET.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()

# --- API CALLS ---
def register_guest(session, password, ua):
    payload = {"app_id": APP_ID, "client_type": 2, "password": password, "source": 2}
    sig = generate_signature(payload)
    body = json.dumps(payload, separators=(",", ":"))
    headers = {
        "User-Agent": ua, "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Connection": "Keep-Alive", "Accept-Encoding": "gzip",
        "Authorization": f"Signature {sig}",
    }
    for attempt in range(1, 4):
        r = session.post(OAUTH_REGISTER_URL, data=body, headers=headers, timeout=15)
        if r.status_code == 200:
            d = r.json()
            if d.get("code") != 0: raise Exception(f"Register failed: {d}")
            return str(d["data"]["uid"])
        if r.status_code == 429:
            time.sleep(3)
            continue
        raise Exception(f"Register HTTP {r.status_code}")
    raise Exception("Register 429 exhausted")

def get_token_legacy(session, uid, password, ua):
    payload = {"uid": uid, "password": password, "response_type": "token",
               "client_type": "2", "client_secret": CLIENT_SECRET, "client_id": "100067"}
    headers = {"User-Agent": ua, "Accept": "application/json",
               "Accept-Encoding": "gzip", "Connection": "Keep-Alive"}
    r = session.post(OAUTH_TOKEN_URL, data=payload, headers=headers, timeout=15)
    if r.status_code != 200: raise Exception(f"Token HTTP {r.status_code}")
    d = r.json()
    at, oid = d.get("access_token"), d.get("open_id")
    if not at or not oid: raise Exception("Token grant failed")
    return at, oid

def send_major_register(session, name, access_token, open_id, server, ua):
    fields = {
        1: name, 2: access_token, 3: open_id,
        5: 102000007, 6: 4, 7: 1, 13: 1,
        14: xor_open_id(open_id),
        15: server["lang"], 16: 2, 20: "2.133.8", 21: 1,
        22: bytes.fromhex(FIELD_22_HEX),
    }
    encrypted = aes_encrypt(assemble_proto(fields))
    headers = {
        "Host": "loginbp.ppmainecoonghj.com", "User-Agent": ua,
        "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": X_GA_SV, "Authorization": "Bearer", "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Content-Length": str(len(encrypted)),
    }
    r = session.post(MAJOR_REGISTER_URL, data=encrypted, headers=headers, timeout=20, verify=False)
    if r.status_code != 200: raise Exception(f"MajorRegister HTTP {r.status_code}")
    return parse_proto(r.content)

def send_newbie_choice(session, account_id, ua=None):
    encrypted = aes_encrypt(assemble_proto({1: int(account_id), 2: 1, 3: 3}))
    headers = {
        "Host": "loginbp.ppmainecoonghj.com", "User-Agent": ua or UNITY_USER_AGENTS[0],
        "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": X_GA_SV, "Authorization": "Bearer", "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Content-Length": str(len(encrypted)),
    }
    try:
        session.post(NEWBIE_URL, headers=headers, data=encrypted, timeout=15, verify=False)
    except: pass

def send_major_login(session, access_token, open_id, server, ua=None):
    fields = {
        3: time.strftime("%Y-%m-%d %H:%M:%S"), 4: "free fire", 5: 1,
        7: "2.133.11", 8: "Android OS 10 / API-29 (QP1A.190711.020/1617006012)",
        9: "Handheld", 10: "Vi India", 11: "WIFI", 12: 1600, 13: 720, 14: "320",
        15: "ARM64 FP ASIMD AES | 2301 | 8", 16: 2799,
        17: "PowerVR Rogue GE8320", 18: "OpenGL ES 3.2 build 1.11@5425693",
        19: "Google|9f7d6b8b-b10c-454a-852d-06332cd498eb",
        20: random.choice(IP_ADDRESSES), 21: server["lang"],
        22: open_id, 23: "4", 24: "Handheld", 25: "realme RMX2189",
        26: server["region"], 29: access_token, 30: 1, 41: "Vi India", 42: "WIFI",
        57: "1ac4b80ecf0478a44203bf8fac6120f5",
        60: 19799, 61: 2536, 62: 5056, 64: 2768, 65: 19999, 66: 2536, 67: 19799, 73: 1,
        74: "/data/app/com.dts.freefiremax-ShI7E0dK8p1IiZ785pvuVQ==/lib/arm64",
        76: 2,
        77: "38f4751a330688ab124c2c804cec90a5|/data/app/com.dts.freefiremax-ShI7E0dK8p1IiZ785pvuVQ==/base.apk",
        78: 2, 79: 2, 81: "64", 83: "2019118527",
        86: "OpenGLES3", 87: 3071, 88: 4, 92: 67920, 93: "android_max",
        94: "KqsHT+UrR1HKqb6+1db+Ofei+NtZr2+hbiBo3yKDL8w+8E3S5qF2IgEEe1fFQFyHRzl4iyHjHp+QsfeLbjJ6+DidTiKxm0ak2uYYa6QR4nAUdlZR",
        95: 111107, 96: '{"cur_rate":null,"support_etc2":true}',
        97: 1, 98: 1, 99: "4", 100: "4", 102: "",
        104: 83812, 105: 1,
        106: "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a",
        107: "1.9393e7b8e53e8aeb",
    }
    encrypted = aes_encrypt(assemble_proto(fields))
    headers = {
        "Host": "loginbp.ppmainecoonghj.com", "User-Agent": ua or UNITY_USER_AGENTS[0],
        "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": X_GA_SV, "Authorization": "Bearer", "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1",
        "Content-Length": str(len(encrypted)),
    }
    r = session.post(MAJOR_LOGIN_URL, data=encrypted, headers=headers, timeout=20, verify=False)
    if r.status_code != 200: raise Exception(f"MajorLogin HTTP {r.status_code}")
    if len(r.content) <= 64: raise Exception("MajorLogin response too short")
    return parse_proto(r.content[64:])

def send_get_login_data(session, jwt_token, server_url, account_id, uid, ua=None):
    """Uses PorTs_pb2 to force registration on the IND server."""
    if not PorTs_pb2:
        return {"error": "PorTs_pb2 not loaded"}
    
    try:
        url = f"{server_url}/GetLoginData"
        host = server_url.split("//")[1] if "//" in server_url else server_url
        
        try: uid_int = int(uid)
        except: uid_int = 0
            
        encrypted = aes_encrypt(assemble_proto({1: uid_int}))
        
        headers = {
            "Host": host, "User-Agent": ua or UNITY_USER_AGENTS[0], 
            "Accept": "*/*", "Accept-Encoding": "deflate, gzip",
            "Authorization": f"Bearer {jwt_token}", "X-Unity-Version": "2018.4.12f1", 
            "X-GA": "v1 1", "X-GA-SV": X_GA_SV, "ReleaseVersion": "OB55", 
            "Content-Type": "application/x-www-form-urlencoded", 
            "Content-Length": str(len(encrypted))
        }
        
        r = session.post(url, data=encrypted, headers=headers, timeout=15, verify=False)
        
        if r.status_code != 200: 
            return {"http_status": r.status_code, "error": f"HTTP {r.status_code}"}
        
        # Parse the response using PorTs_pb2
        candidates = [r.content]
        if len(r.content) > 64: 
            candidates.append(r.content[64:])
            
        for blob in candidates:
            try:
                proto = PorTs_pb2.GetLoginData()
                proto.ParseFromString(blob)
                if proto.AccountUID or proto.Online_IP_Port or proto.AccountIP_Port:
                    return {
                        "AccountUID": int(proto.AccountUID) if proto.AccountUID else None, 
                        "Region": proto.Region or None, 
                        "AccountName": proto.AccountName or None, 
                        "Online_IP_Port": proto.Online_IP_Port or None, 
                        "AccountIP_Port": proto.AccountIP_Port or None
                    }
            except Exception: 
                continue
        return {"error": "could not parse"}
    except Exception as e: 
        return {"error": str(e)[:200]}

# --- WORKER ---
def create_account(index, prefix, region, deadline):
    if time.time() > deadline:
        return {"index": index, "success": False, "error": "timeout"}

    server = REGION_CONFIG.get(region, REGION_CONFIG["IND"])
    session = requests.Session()
    session.verify = False
    try:
        msdk_ua = pick_msdk_ua()
        unity_ua = pick_unity_ua()
        password = generate_password()

        uid = register_guest(session, password, msdk_ua)
        access_token, open_id = get_token_legacy(session, uid, password, msdk_ua)

        nickname = None
        account_id = None
        
        for attempt in range(1, 6):
            if time.time() > deadline: raise RuntimeError("deadline reached")
            try:
                candidate = generate_nickname(prefix)
                reg_resp = send_major_register(session, candidate, access_token, open_id, server, unity_ua)
                account_id = reg_resp.get(3)
                if account_id:
                    nickname = candidate
                    break
            except Exception:
                time.sleep(0.3)

        if not account_id or not nickname:
            raise RuntimeError("MajorRegister failed")

        send_newbie_choice(session, account_id, ua=unity_ua)
        
        login_resp = send_major_login(session, access_token, open_id, server, unity_ua)
        jwt = login_resp.get(8)
        if isinstance(jwt, bytes): jwt = jwt.decode("utf-8", errors="ignore")
        if not jwt: raise RuntimeError("JWT missing")

        # Call GetLoginData to force it to register in IND instead of NA
        login_data = None
        if region == "IND":
            login_data = send_get_login_data(session, jwt, IND_SERVER_URL, account_id, uid, unity_ua)

        return {
            "index": index,
            "success": True,
            "uid": uid,
            "password": password,
            "name": nickname,
            "account_id": str(account_id),
            "jwt": jwt,
            "open_id": open_id,
            "region": region,
            "status": "unregistered" if not login_data else "registered",
            "login_data": login_data,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        return {"index": index, "success": False, "error": str(e)[:150], "region": region}
    finally:
        session.close()

# --- FLASK ROUTES ---
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "VISWA API (Unregistered Mode)",
        "status": "online",
        "max_count": MAX_COUNT,
        "example": "/generate?NAME=VISWA&REGION=IND&COUNT=1&password=jeethurviswa"
    })

@app.route("/generate", methods=["GET", "POST"])
def generate():
    json_body = request.get_json(silent=True) or {}
    
    password = request.headers.get("X-Api-Password") or request.args.get("password") or json_body.get("password") or request.form.get("password")
    if password != USAGE_PASSWORD:
        return jsonify({"success": False, "error": "Invalid password"}), 401

    name = json_body.get("NAME") or request.args.get("NAME") or request.form.get("NAME") or "VISWA"
    region = json_body.get("REGION") or request.args.get("REGION") or request.form.get("REGION") or "IND"
    count_str = json_body.get("COUNT") or request.args.get("COUNT") or request.form.get("COUNT") or "1"

    region = str(region).strip().upper()
    if region not in REGION_CONFIG:
        return jsonify({"success": False, "error": f"Region '{region}' not available"}), 400

    try:
        count = int(count_str)
        if not (1 <= count <= MAX_COUNT): raise ValueError
    except:
        return jsonify({"success": False, "error": f"COUNT must be 1-{MAX_COUNT}"}), 400

    start_time = time.time()
    deadline = start_time + TIME_BUDGET_SECONDS
    results = []
    results_lock = threading.Lock()

    def worker(idx):
        res = create_account(idx, name, region, deadline)
        with results_lock:
            results.append(res)

    with ThreadPoolExecutor(max_workers=min(count, 8)) as executor:
        futures = [executor.submit(worker, i) for i in range(1, count + 1)]
        for f in futures:
            try: f.result(timeout=max(1, deadline - time.time()))
            except: pass

    results.sort(key=lambda x: x.get("index", 999))
    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    return jsonify({
        "success": len(successful) > 0,
        "request": {"NAME": name, "REGION": region, "COUNT": count},
        "generated": len(successful),
        "failed": len(failed),
        "time_seconds": round(time.time() - start_time, 2),
        "accounts": successful,
        "errors": failed
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
