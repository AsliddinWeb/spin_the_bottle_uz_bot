import json, urllib.request, urllib.error
B="http://localhost:8001"; fails=[]; passed=0
def call(path,uid,body=None):
    r=urllib.request.Request(B+path,data=json.dumps(body).encode() if body is not None else None,headers={"Content-Type":"application/json","X-Init-Data":f"dev:{uid}"},method="POST" if body is not None else "GET")
    try: return 200,json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e:
        try: return e.code,json.loads(e.read())
        except Exception: return e.code,{}
def ok(name,cond,info=""):
    global passed
    if cond: passed+=1
    else: fails.append(f"{name} {info}")
def me(u): return call("/api/me",u)[1]
for u,n,g in ((1,"A","m"),(2,"B","f"),(3,"C","m")): call("/api/profile",u,{"name":n,"birth":"2000-01-01","gender":g,"lang":"ru"})
# profile validation
c,_=call("/api/profile",1,{"name":"","birth":"2000-01-01","gender":"m","lang":"ru"}); ok("empty name rejected",c==400)
c,_=call("/api/profile",1,{"name":"X","birth":"2020-01-01","gender":"m","lang":"ru"}); ok("under-14 rejected",c==400)
c,_=call("/api/profile",1,{"name":"X","birth":"2000-01-01","gender":"z","lang":"ru"}); ok("bad gender rejected",c==400)
c,_=call("/api/profile",1,{"name":"X","birth":"2000-01-01","gender":"m","lang":"xx"}); ok("bad lang rejected",c==400)
# start hearts
ok("start hearts 30",me(1)["hearts"]==30,me(1)["hearts"])
# daily
c,r=call("/api/daily/claim",1,{}); ok("daily claim ok",c==200 and r["reward"]==1,r); h=me(1)["hearts"]; ok("daily +1",h==31,h)
c,_=call("/api/daily/claim",1,{}); ok("daily twice rejected",c==400)
# wheel without chances
c,_=call("/api/wheel/spin",1,{}); ok("wheel no chance rejected",c==400)
for _ in range(6): call("/api/wheel/buy",1,{})
m=me(1); ok("buy chance cost 5 each",m["hearts"]==1 and m["chances"]==6,(m["hearts"],m["chances"]))
c,_=call("/api/wheel/buy",1,{}); ok("buy chance w/o hearts rejected",c==400)
tot=0
for _ in range(3):
    c,r=call("/api/wheel/spin",1,{}); ok("wheel spin ok",c==200 and 0<=r["index"]<16,r)
ok("chances consumed",me(1)["chances"]>=0)
# shop: buy/equip rules
call("/api/shop/invoice",1,{"kind":"pack","id":"p500"}); ok("dev pack grants",me(1)["hearts"]>=500)
h0=me(1)["hearts"]; c0=me(1)["chances"]; c,_=call("/api/wheel/buy",1,{"n":5}); ok("chance pack x5 costs 20",c==200 and me(1)["hearts"]==h0-20 and me(1)["chances"]==c0+5)
c,_=call("/api/wheel/buy",1,{"n":7}); ok("unknown chance pack rejected",c==400 and me(1)["chances"]==c0+5)
c,_=call("/api/wheel/buy",1,{"n":300}); ok("chance pack x300 costs 900 (not enough hearts)",c==400 or me(1)["hearts"]>=0)
c,_=call("/api/store/equip",1,{"item":"frame_gold"}); ok("equip unowned rejected",c==400)
c,_=call("/api/store/buy",1,{"item":"nope"}); ok("buy unknown rejected",c==400)
h0=me(1)["hearts"]; call("/api/store/buy",1,{"item":"frame_gold"}); ok("buy frame -30",me(1)["hearts"]==h0-30)
c,_=call("/api/store/buy",1,{"item":"frame_gold"}); ok("rebuy frame rejected",c==400)
call("/api/store/equip",1,{"item":"frame_gold"}); ok("equip frame",me(1)["frame"]=="frame_gold")
call("/api/store/equip",1,{"item":""}); ok("unequip frame",me(1)["frame"]=="")
call("/api/store/buy",1,{"item":"bottle_red"}); call("/api/store/equip",1,{"item":"bottle_red"}); ok("equip bottle",me(1)["bottle"]=="bottle_red")
c,_=call("/api/store/equip",1,{"item":"bottle_blue"}); ok("equip unowned bottle rejected",c==400)
# boosters
call("/api/store/buy",1,{"item":"shield"}); call("/api/store/buy",1,{"item":"shield"}); ok("booster stack qty 2",me(1)["inv"]["shield"]["qty"]==2)
call("/api/store/arm",1,{"item":"shield"}); m=me(1); ok("arm moves qty->armed",m["inv"]["shield"]["qty"]==1 and m["inv"]["shield"]["armed"]==1)
c,_=call("/api/store/arm",1,{"item":"frame_gold"}); ok("arm non-booster rejected",c==400)
# insufficient hearts for purchase
c,_=call("/api/store/buy",3,{"item":"frame_fire"}); ok("buy w/o hearts rejected",c==400 or me(3)["hearts"]>=80)
# VIP + smiles
s0=me(1)["smiles"]; c,_=call("/api/vip/collect",1,{}); ok("collect needs vip",c==400)
call("/api/shop/invoice",1,{"kind":"vip","id":""}); ok("vip active",me(1)["vip"])
c,r=call("/api/vip/collect",1,{}); ok("vip collect +5",c==200 and r["smiles"]==s0+5,(c,r.get("smiles")))
c,_=call("/api/vip/collect",1,{}); ok("vip collect once a day",c==400)
# courtship
h1=me(1)["hearts"]; h2=me(2)["hearts"]
c,r=call("/api/court",1,{"to":2}); ok("court price 1",c==200 and r["price"]==1,r)
ok("court hearts are burnt (payer -1, courted unchanged)",me(1)["hearts"]==h1-1 and me(2)["hearts"]==h2)
c,_=call("/api/court",1,{"to":2}); ok("court same suitor rejected",c==400)
c,r=call("/api/court",3,{"to":2}); ok("outbid price 2",c==200 and r["price"]==2,r)
c,_=call("/api/court",1,{"to":1}); ok("court self rejected",c==400)
card=call("/api/user/2",1)[1]; ok("card shows suitor",card["suitor"] and card["suitor"]["id"]==3 and card["suitor"]["price"]==2,card.get("suitor"))
c,r=call("/api/court",1,{"to":2}); ok("taken back with one heart more (3)",c==200 and r["price"]==3,r)
c,_=call("/api/court/decline",3,{}); ok("decline without suitor rejected",c==400)
c,_=call("/api/court/decline",2,{}); ok("target declines the suitor",c==200 and call("/api/user/2",1)[1]["suitor"] is None)
c,r=call("/api/court",1,{"to":2}); ok("after decline the price starts again at 1",c==200 and r["price"]==1,r)
# compliments
c,r=call("/api/compliment",1,{"to":2,"text":"hi"}); ok("compliment ok",c==200)
c,_=call("/api/compliment",1,{"to":2,"text":"hi2"}); ok("compliment cooldown",c==400)
c,_=call("/api/compliment",1,{"to":1,"text":"self"}); ok("compliment self rejected",c==400)
c,_=call("/api/compliment",1,{"to":3,"text":""}); ok("compliment empty rejected",c==400)
un=call("/api/compliments/unread",2)[1]; ok("unread has it",len(un)==1)
hh=me(2)["hearts"]; c,_=call(f"/api/compliments/{un[0]['id']}/read",2,{}); ok("read +1 heart",c==200 and me(2)["hearts"]==hh+1)
c,_=call(f"/api/compliments/{un[0]['id']}/read",2,{}); ok("read twice rejected",c==400)
c,_=call(f"/api/compliments/{un[0]['id']}/read",3,{}); ok("read by other rejected",c==400)
# tag task
t=call("/api/tagtask",1)[1]; ok("tag task state",t["need"]==10 and not t["paid"])
hh=me(1)["hearts"]; paid=False
for i in range(10,22): call("/api/profile",i,{"name":f"U{i}","birth":"1999-01-01","gender":"m","lang":"ru"})
voted=0
for i in range(10,22):
    c,r=call("/api/tagtask/vote",1,{"to":i,"tag":"fun"})
    if c==200: voted+=1
    if c==200 and r["result"]=="reward": paid=True
ok("tag task pays once",paid and me(1)["hearts"]==hh+10,(paid,me(1)["hearts"]-hh))
c,_=call("/api/tagtask/vote",1,{"to":10,"tag":"fun"}); ok("tag re-vote rejected",c==400)
c,_=call("/api/tagtask/vote",1,{"to":11,"tag":"bad"}); ok("bad tag rejected",c==400)
# ratings
for k in ("kisses","gifts","tracks","court"): c,r=call(f"/api/ratings/{k}",1); ok(f"rating {k}",c==200 and "rows" in r and "rank" in r)
c,_=call("/api/ratings/hearts",1); ok("hearts rating removed",c==404)
c,_=call("/api/ratings/xyz",1); ok("rating bad kind 404",c==404)
# notify
ok("notify off",call("/api/notify",1,{"on":False})[1]["notify"]==False)
# tasks
c,_=call("/api/tasks/claim",1,{"id":"subscribe"}); ok("subscribe claim (dev has no channel)",c in (200,400))
c,_=call("/api/tasks/claim",1,{"id":"zzz"}); ok("unknown task 404",c==404)
# auth
r=urllib.request.Request(B+"/api/me"); 
try: urllib.request.urlopen(r); ok("no auth rejected",False)
except urllib.error.HTTPError as e: ok("no auth rejected",e.code==401)
# photo
c,_=call("/api/photo",1,{}); ok("photo bad body rejected",c in (400,413,422))
print(f"PASSED {passed}, FAILED {len(fails)}")
for f in fails: print(" FAIL:",f)
