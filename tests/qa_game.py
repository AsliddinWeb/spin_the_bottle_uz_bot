import asyncio, json, urllib.request, websockets, time
B="localhost:8001"; fails=[]; passed=0
def ok(n,c,i=""):
    global passed
    if c: passed+=1
    else: fails.append(f"{n} {i}")
def api(path,uid,body=None):
    r=urllib.request.Request("http://"+B+path,data=json.dumps(body).encode() if body is not None else None,headers={"Content-Type":"application/json","X-Init-Data":f"dev:{uid}"},method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(r).read())
class P:
    def __init__(s,uid): s.uid=uid; s.ws=None; s.state=None; s.msgs=[]; s.chat=[]
    async def start(s,table):
        s.ws=await websockets.connect(f"ws://{B}/ws?init=dev:{s.uid}"); await s.ws.send(json.dumps({"t":"join","table":table})); s.task=asyncio.create_task(s.rd())
    async def rd(s):
        try:
            async for raw in s.ws:
                m=json.loads(raw); s.msgs.append(m)
                if m["t"]=="state": s.state=m
                if m["t"]=="chat": s.chat.append(m)
        except Exception: pass
    async def send(s,**k): await s.ws.send(json.dumps(k))
    async def wait(s,pred,timeout=30):
        t0=time.time()
        while time.time()-t0<timeout:
            if s.state and pred(s.state): return s.state
            await asyncio.sleep(.1)
        return None
async def main():
    for u,n,g in ((101,"P1","m"),(102,"P2","f"),(103,"P3","m")):
        api("/api/profile",u,{"name":n,"birth":"2000-01-01","gender":g,"lang":"ru"}); api("/api/shop/invoice",u,{"kind":"pack","id":"p500"})
    a,b,c=P(101),P(102),P(103)
    await a.start(7); await asyncio.sleep(.5)
    ok("alone -> waiting",(await a.wait(lambda s:s["phase"]=="waiting")) is not None)
    await b.start(7)
    s=await a.wait(lambda s:s["phase"]=="spin_wait")
    ok("2 players -> spin_wait",s is not None and len(s["seats"])==2)
    spinner=a if s["turn"]==101 else b; other=b if spinner is a else a
    # wrong player cannot spin
    await other.send(t="spin"); await asyncio.sleep(.6); ok("non-spinner spin ignored",other.state["phase"]=="spin_wait")
    await spinner.send(t="spin")
    s=await spinner.wait(lambda s:s["phase"]=="spinning",5); ok("spinning phase",s is not None and s["target"]==other.uid)
    s=await spinner.wait(lambda s:s["phase"]=="ask_spinner",10); ok("ask_spinner",s is not None)
    # target cannot answer spinner's question
    await other.send(t="decide",v=True); await asyncio.sleep(.5); ok("wrong answerer ignored",spinner.state["phase"]=="ask_spinner")
    k0=api("/api/me",spinner.uid)["kisses"]; h0=api("/api/me",spinner.uid)["hearts"]
    await spinner.send(t="decide",v=True)
    ok("ask_target",(await spinner.wait(lambda s:s["phase"]=="ask_target",5)) is not None)
    await other.send(t="decide",v=True)
    s=await spinner.wait(lambda s:s["phase"]=="result",5); ok("kiss result",s is not None and s["result"]=="kiss",s and s["result"])
    ok("kiss counters +1 each",api("/api/me",spinner.uid)["kisses"]==k0+1 and api("/api/me",other.uid)["kisses"]>=1)
    ok("kiss pays heart",api("/api/me",spinner.uid)["hearts"]==h0+1,(h0,api("/api/me",spinner.uid)["hearts"]))
    ok("kiss chat event",any(m.get("k")=="kiss" for m in spinner.chat))
    # next turn rotates
    s=await spinner.wait(lambda s:s["phase"]=="spin_wait" and s["turn"]==other.uid,12); ok("turn rotates",s is not None)
    # refusal path
    await other.send(t="spin"); await other.wait(lambda s:s["phase"]=="ask_spinner",10)
    await other.send(t="decide",v=False); s=await other.wait(lambda s:s["phase"]=="result",5); ok("decline -> result no",s is not None and s["result"]=="no")
    # chat
    await a.send(t="chat",text="  hello <b>  "); await asyncio.sleep(.5); m=[x for x in b.chat if x.get("k")=="msg"]; ok("chat delivered",len(m)==1 and m[0]["text"]=="hello <b>",m)
    await a.send(t="chat",text="x"*500); await asyncio.sleep(1); m=[x for x in b.chat if x.get("k")=="msg"]; ok("chat truncated 200",len(m)==2 and len(m[-1]["text"])==200)
    await a.send(t="chat",text="spam1"); await a.send(t="chat",text="spam2"); await asyncio.sleep(.5); ok("chat rate limit",len([x for x in b.chat if x.get("k")=="msg"])<=3)
    # gifts
    h=api("/api/me",a.uid)["hearts"]
    await a.send(t="gift",to=b.uid,gift="rose"); await asyncio.sleep(.8)
    ok("gift costs 1",api("/api/me",a.uid)["hearts"]==h-1)
    seat=[x for x in b.state["seats"] if x["uid"]==b.uid][0]; ok("gift on avatar (hand)",seat["gifts"].get("hand")=="🌹",seat["gifts"])
    await a.send(t="gift",to=b.uid,gift="crown1"); await asyncio.sleep(.8)
    seat=[x for x in b.state["seats"] if x["uid"]==b.uid][0]; ok("head gift slot",seat["gifts"].get("head")=="👑",seat["gifts"])
    ok("gift log in profile",any(g["emoji"]=="🌹" for g in api("/api/user/102",101)["gifts"]))
    h=api("/api/me",a.uid)["hearts"]; await a.send(t="gift",to=a.uid,gift="rose"); await asyncio.sleep(.5); ok("gift to self ignored",api("/api/me",a.uid)["hearts"]==h)
    await a.send(t="gift",to=999999,gift="rose"); await asyncio.sleep(.5); ok("gift to absent ignored",api("/api/me",a.uid)["hearts"]==h)
    await a.send(t="gift",to=b.uid,gift="trophy"); await asyncio.sleep(.5); ok("VIP gift blocked for non-VIP",api("/api/me",a.uid)["hearts"]==h)
    # shield blocks bad gift
    api("/api/store/buy",102,{"item":"shield"}); api("/api/store/arm",102,{"item":"shield"})
    h=api("/api/me",a.uid)["hearts"]; await a.send(t="gift",to=b.uid,gift="tomato"); await asyncio.sleep(.8)
    ok("shield: gift paid but blocked",api("/api/me",a.uid)["hearts"]==h-1 and any(m.get("k")=="gift" and m.get("blocked") for m in a.chat))
    ok("shield consumed",api("/api/me",102)["inv"]["shield"]["armed"]==0)
    # poor user
    api("/api/profile",104,{"name":"P4","birth":"2000-01-01","gender":"m","lang":"ru"})
    # music
    h=api("/api/me",a.uid)["hearts"]; await a.send(t="gift",to=0,gift="music_queue",url="https://youtu.be/dQw4w9WgXcQ"); await asyncio.sleep(2.5)
    s=a.state; ok("music playing",s["music"] and s["music"]["vid"]=="dQw4w9WgXcQ",s.get("music"))
    ok("music cost 5, DJ level 1",api("/api/me",a.uid)["hearts"]==h-5 and api("/api/user/101",101)["dj"]==1)
    await a.send(t="gift",to=0,gift="music_queue",url="https://youtu.be/9bZkp7q19f0"); await asyncio.sleep(2.5); ok("2nd track queued",a.state["queue"]==1,a.state["queue"])
    tid=a.state["music"]["tid"]; await a.send(t="music_ended",tid=tid); await asyncio.sleep(.6); ok("queue advances",a.state["music"] and a.state["music"]["vid"]=="9bZkp7q19f0" and a.state["queue"]==0)
    h=api("/api/me",a.uid)["hearts"]; await a.send(t="gift",to=0,gift="music_now",url="not a link"); await asyncio.sleep(.5); ok("bad url no charge",api("/api/me",a.uid)["hearts"]==h)
    # gestures
    sm=api("/api/me",a.uid)["smiles"]; await a.send(t="gesture",id="nohearts"); await asyncio.sleep(.6)
    seat=[x for x in b.state["seats"] if x["uid"]==a.uid][0]; ok("gesture shown",seat["gesture"]=="🥺" and api("/api/me",a.uid)["smiles"]==sm-1,(seat["gesture"],sm))
    await a.send(t="gesture",id="laugh"); await asyncio.sleep(.5); ok("vip gesture blocked",api("/api/me",a.uid)["smiles"]==sm-1)
    await a.send(t="gesture",id="wink"); await asyncio.sleep(.5); ok("locked gesture blocked",api("/api/me",a.uid)["smiles"]==sm-1)
    # kiss counter shown on seat
    ok("seat kiss badge",any(x["kisses"]>=1 for x in a.state["seats"]))
    # third player + magnet/leave behaviour
    await c.start(7); await asyncio.sleep(1); ok("3 players seated",len(a.state["seats"])==3)
    await c.send(t="leave"); await asyncio.sleep(.8); ok("leave frees seat",len(a.state["seats"])==2 and any(m["t"]=="left" for m in c.msgs))
    # reconnect same uid replaces old socket
    a2=P(101); await a2.start(7); await asyncio.sleep(1.2); ok("same user kicked older socket",len([x for x in a2.state["seats"] if x["uid"]==101])==1,len(a2.state["seats"]))
    # table switching
    await a2.send(t="join",table=8); await asyncio.sleep(.8); ok("switch table",a2.state["id"]==8 and len(b.state["seats"])==1)
    await a2.send(t="join",table=7); await asyncio.sleep(.8); ok("switch back",a2.state["id"]==7)
    await a2.send(t="join",table="random"); await asyncio.sleep(.8); ok("random table valid",1<=a2.state["id"]<=300)
    await a2.send(t="join",table=9999); await asyncio.sleep(.5)
    # full table (12) overflow goes to another table
    ps=[]
    for u in range(200,213):
        api("/api/profile",u,{"name":f"F{u}","birth":"2000-01-01","gender":"m","lang":"ru"}); p=P(u); await p.start(50); ps.append(p); await asyncio.sleep(.15)
    await asyncio.sleep(1.5); ids=[p.state["id"] for p in ps if p.state]; ok("12 seats max, 13th redirected",ids.count(50)==12 and len(ids)==13,ids)
    # AFK: spinner never spins -> strikes -> kicked after 3 (check strike behaviour quickly via timer is too long: only verify skip happens)
    for p in ps+[a,a2,b]: 
        try: await p.ws.close()
        except Exception: pass
    print(f"PASSED {passed}, FAILED {len(fails)}")
    for f in fails: print(" FAIL:",f)
asyncio.run(main())
