import asyncio, json, urllib.request, urllib.error, websockets, time
B="localhost:8001"
def raw(path,uid,body=None,data=None,ct="application/json"):
    r=urllib.request.Request("http://"+B+path,data=data if data is not None else (json.dumps(body).encode() if body is not None else None),headers={"Content-Type":ct,"X-Init-Data":f"dev:{uid}"},method="POST" if (body is not None or data is not None) else "GET")
    try: return urllib.request.urlopen(r).status
    except urllib.error.HTTPError as e: return e.code
res=[]
def chk(n,c): res.append(("PASS " if c else "FAIL ")+n)
# SQL-injection-ish / odd input must not 500
for p,b in [("/api/profile",{"name":"'); DROP TABLE users;--","birth":"2000-01-01","gender":"m","lang":"ru"}),("/api/compliment",{"to":301,"text":"<script>alert(1)</script>"}),("/api/court",{"to":-5}),("/api/tagtask/vote",{"to":"x","tag":"fun"}),("/api/store/buy",{"item":"' OR 1=1"})]:
    c=raw(p,301,b); chk(f"{p} no 500 ({c})",c<500)
chk("users table intact",raw("/api/me",301)==200)
# profile name stored safely and escaped by client (server keeps text)
chk("photo: non-image body rejected",raw("/api/photo",301,data=b"not an image",ct="image/jpeg")==400)
chk("photo: >3MB rejected",raw("/api/photo",301,data=b"0"*3_100_000,ct="image/jpeg")==413)
chk("unknown user card 404",raw("/api/user/99999999",301)==404)
chk("report on unknown target no 500",raw("/api/report",301,{"to":99999999})<500)
# websocket: bad auth closes; garbage frames survive; huge frame survive
async def ws():
    try:
        w=await websockets.connect(f"ws://{B}/ws?init=bad"); 
        try: await asyncio.wait_for(w.recv(),3); chk("bad ws auth closed",False)
        except Exception: chk("bad ws auth closed",True)
    except Exception: chk("bad ws auth closed",True)
    w=await websockets.connect(f"ws://{B}/ws?init=dev:301"); await w.send(json.dumps({"t":"join","table":31}))
    for junk in ["not json","[]","123",'{"t":"gift","to":"abc","gift":1}','{"t":"spin"}','{"t":"decide"}','{"t":"join","table":"zzz"}','{"t":"chat","text":null}','{"t":"gesture","id":5}','{"t":"pm"}']:
        await w.send(junk)
    await asyncio.sleep(1.2)
    await w.send(json.dumps({"t":"ping"})); m=None
    try:
        for _ in range(20):
            m=json.loads(await asyncio.wait_for(w.recv(),2))
            if m["t"]=="pong": break
    except Exception: pass
    chk("ws survives junk frames",m is not None and m["t"]=="pong")
    await w.close()
asyncio.run(ws())
print("\n".join(res))
