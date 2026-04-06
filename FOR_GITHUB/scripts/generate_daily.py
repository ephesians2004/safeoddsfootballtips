#!/usr/bin/env python3
"""
SafeOdds Daily Page Generator v2
- Fetches today's bundle from Cloudflare Worker (fixtures + stats + h2h + odds)
- Runs the Poisson prediction engine (same logic as index.html)
- Generates/overwrites 18 SEO base pages (e.g. /prime-safe/index.html)
- Generates 18 dated static snapshot pages (e.g. /prime-safe/2026-04-06/index.html)
- Updates sitemap.xml
Run via GitHub Actions every day at 8 AM UTC.
"""

import os, json, math, hashlib, urllib.request, urllib.error
from datetime import date

# ─── Config ──────────────────────────────────────────────────────────────────
today      = date.today()
TODAY_STR  = today.strftime("%B %d, %Y")        # April 06, 2026
TODAY_ISO  = today.isoformat()                   # 2026-04-06
TODAY_SLUG = today.isoformat()                   # used in URLs
TODAY_API  = today.strftime("%Y%m%d")            # 20260406
DOMAIN     = "https://www.safeoddsfootballtips.com"
API_URL    = f"https://football-ai-backend.ephesians2004.workers.dev/v2/bundle?date={TODAY_API}"
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── All 18 Categories (matches index.html CF config) ────────────────────────
CATEGORIES = [
    {
        "slug": "prime-safe", "key": "PRIME_SAFE", "name": "Prime Safe", "vip": False,
        "title": "Safe Football Predictions Today | Free Tips",
        "desc": "Free prime safe football predictions updated daily. Low-risk AI-selected matches with high win probability. Best safe football tips for today.",
        "h1": "Safe Football Predictions Today",
        "intro": "Prime Safe picks are our most reliable daily tips — AI-selected matches where statistical confidence is highest. Perfect for bettors who prefer consistent wins over big odds.",
        "markets": ["HOME_WIN","AWAY_WIN","HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW"],
        "min_conf": 48, "n_tips": 2,
    },
    {
        "slug": "daily-5-odds", "key": "DAILY_5PLUS", "name": "Daily 5+ Odds", "vip": False,
        "title": "Daily 5 Odds Football Tips Today | Accumulator Predictions",
        "desc": "AI-selected football accumulator tips combining to 5.00+ odds daily. Free 5 odds football predictions with team stats and analysis.",
        "h1": "Daily 5 Odds Accumulator Tips Today",
        "intro": "Our Daily 5 Odds accumulator combines 3 well-researched picks to reach odds around 5.00. Each selection is backed by our Poisson probability engine.",
        "markets": ["HOME_WIN","AWAY_WIN","HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW","OVER_1.5","OVER_2.5","UNDER_3.5"],
        "min_conf": 50, "n_tips": 3,
    },
    {
        "slug": "daily-10-odds", "key": "DAILY_10PLUS", "name": "Daily 10+ Odds", "vip": False,
        "title": "Daily 10 Odds Football Tips Today | High Odds Accumulator",
        "desc": "AI-selected football tips combining to 10.00+ odds daily. Free 10 odds accumulator predictions updated every morning.",
        "h1": "Daily 10 Odds Accumulator Predictions Today",
        "intro": "The Daily 10 Odds accumulator targets bigger returns — 4 picks combining to 10.00+ odds. Our AI filters for value across all major leagues.",
        "markets": ["HOME_WIN","AWAY_WIN","HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW","OVER_1.5","UNDER_3.5"],
        "min_conf": 48, "n_tips": 4,
    },
    {
        "slug": "over-under", "key": "OVER_UNDER", "name": "Over/Under Tips", "vip": False,
        "title": "Over Under Football Predictions Today | Goals Tips Free",
        "desc": "Free Over 2.5, Over 1.5 and Under 2.5 football predictions updated daily. AI-powered goals predictions for today's matches.",
        "h1": "Over Under Football Predictions Today",
        "intro": "Over/Under tips focus on total goals — one of the most consistent football betting markets. Our Poisson model calculates expected goals for every match.",
        "markets": ["OVER_1.5","UNDER_2.5","UNDER_3.5","UNDER_4.5"],
        "min_conf": 50, "n_tips": 2,
    },
    {
        "slug": "double-tips", "key": "DOUBLE_TIPS", "name": "Double Tips", "vip": False,
        "title": "Football Double Tips Today | 2-Fold Accumulator Predictions",
        "desc": "Free football double tips updated daily. AI-selected 2-fold accumulator predictions for today's best matches.",
        "h1": "Football Double Tips Today",
        "intro": "Double tips combine two of the day's most predictable matches for solid, consistent returns. Great for bettors who want to step up from singles.",
        "markets": ["HOME_WIN_BTTS","AWAY_WIN_BTTS","HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW"],
        "min_conf": 48, "n_tips": 2,
    },
    {
        "slug": "single-game", "key": "SINGLE_GAME", "name": "Single Game Tip", "vip": False,
        "title": "Best Football Prediction Today | Single Game Tip",
        "desc": "One top AI football prediction today — our single highest-confidence pick. Free best bet of the day updated daily.",
        "h1": "Best Single Football Prediction Today",
        "intro": "The Single Game tip is our highest-confidence pick of the day — one match, one prediction, maximum statistical backing.",
        "markets": ["HOME_WIN","AWAY_WIN","HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW"],
        "min_conf": 50, "n_tips": 1,
    },
    {
        "slug": "daily-2-2-5", "key": "DAILY_2_2_5", "name": "Daily 2–2.5 Odds", "vip": False,
        "title": "2 Odds Football Tips Today | 2.5 Odds Predictions Free",
        "desc": "Football tips at 2.00–2.50 odds — the high win-rate value bet range. AI-selected 2 odds football predictions updated daily.",
        "h1": "Daily 2–2.5 Odds Football Tips Today",
        "intro": "The 2–2.5 range is the sweet spot for consistent profit. Our AI identifies underpriced outcomes where the bookmaker edge is smallest.",
        "markets": ["HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW","UNDER_2.5","UNDER_3.5"],
        "min_conf": 50, "n_tips": 5,
    },
    {
        "slug": "high-value", "key": "HIGH_VALUE_1", "name": "High Value Tips", "vip": False,
        "title": "High Value Football Betting Tips Today | Value Bets Free",
        "desc": "Free high value football betting tips where AI probability exceeds bookmaker odds. Daily value bet predictions updated every morning.",
        "h1": "High Value Football Betting Tips Today",
        "intro": "High Value tips are selected on mathematical edge — where our model finds outcomes where the true probability is higher than what bookmakers are offering.",
        "markets": ["HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW","OVER_1.5","UNDER_3.5","UNDER_4.5","HOME_OVER_0.5","AWAY_OVER_0.5"],
        "min_conf": 70, "n_tips": 6,
    },
    {
        "slug": "high-value-2", "key": "HIGH_VALUE_2", "name": "High Value 2", "vip": False,
        "title": "High Value Football Tips 2 Today | BTTS and Goals Predictions",
        "desc": "High value football tips featuring BTTS, clean sheets and goals markets. Free AI value bets updated daily.",
        "h1": "High Value Football Tips 2 — BTTS & Goals",
        "intro": "Our second High Value category targets the goals and BTTS markets — clean sheets, both teams scoring and win/loss outcomes priced above true probability.",
        "markets": ["HOME_WIN","AWAY_WIN","DRAW","OVER_2.5","UNDER_2.5","BTTS_YES","HOME_CLEAN_SHEET"],
        "min_conf": 55, "n_tips": 6,
    },
    # VIP Categories
    {
        "slug": "elite-vip", "key": "ELITE_VIP", "name": "Elite VIP Tips", "vip": True,
        "title": "Elite VIP Football Tips Today | Premium AI Predictions",
        "desc": "Premium Elite VIP football predictions — our highest confidence tips across all markets. AI-powered daily picks for serious bettors.",
        "h1": "Elite VIP Football Predictions Today",
        "intro": "Elite VIP combines our most confident picks across multiple markets — goal lines, match results and more. Our strictest confidence threshold: 58%+.",
        "markets": ["HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW","HOME_OVER_0.5","AWAY_OVER_0.5","OVER_1.5","UNDER_3.5","UNDER_4.5"],
        "min_conf": 58, "n_tips": 5,
    },
    {
        "slug": "correct-score", "key": "CORRECT_SCORE", "name": "Correct Score VIP", "vip": True,
        "title": "Correct Score Football Predictions Today | Exact Score Tips",
        "desc": "AI-powered correct score football predictions for today. Exact scoreline tips using Poisson distribution modelling updated daily.",
        "h1": "Correct Score Football Predictions Today",
        "intro": "Correct Score predictions use Poisson distribution modelling and historical score patterns to identify the most probable exact scorelines.",
        "markets": ["EXACT_1_1","EXACT_2_1_HOME","EXACT_3_1_HOME","EXACT_0_1_AWAY","EXACT_0_2_AWAY","EXACT_0_3_AWAY"],
        "min_conf": 10, "n_tips": 6,
    },
    {
        "slug": "ht-ft-vip", "key": "HT_FT_VIP", "name": "HT/FT VIP", "vip": True,
        "title": "HT FT Football Predictions Today | Halftime Fulltime Tips",
        "desc": "Halftime fulltime football predictions updated daily. AI-powered HT/FT tips for today's matches — specialist market predictions.",
        "h1": "Halftime Fulltime Football Predictions Today",
        "intro": "HT/FT tips forecast both the halftime AND fulltime result — a specialist high-odds market where our model analyses momentum and in-game patterns.",
        "markets": ["HT_FT_HOME_HOME","HT_FT_DRAW_HOME","HT_FT_AWAY_AWAY","HT_FT_DRAW_AWAY"],
        "min_conf": 10, "n_tips": 6,
    },
    {
        "slug": "50-plus-odds", "key": "DAILY_50_ODDS", "name": "50+ Odds Tips", "vip": True,
        "title": "50 Odds Football Tips Today | High Odds Accumulator Free",
        "desc": "High odds accumulator football tips combining to 50+ odds daily. AI-selected 50 odds predictions for maximum returns.",
        "h1": "50+ Odds Football Accumulator Today",
        "intro": "Our 50+ Odds accumulator combines 8–10 picks to exceed 50.00 total odds. High risk, high reward — every selection is individually backed by our AI engine.",
        "markets": ["HOME_WIN","AWAY_WIN","HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW","OVER_1.5","OVER_2.5","OVER_3.5","UNDER_3.5","UNDER_4.5","HOME_OVER_0.5","AWAY_OVER_0.5","HOME_WIN_BTTS","AWAY_WIN_BTTS"],
        "min_conf": 45, "n_tips": 10,
    },
    {
        "slug": "prime-plus", "key": "PRIME_PLUS", "name": "Prime Plus VIP", "vip": True,
        "title": "Prime Plus Football Predictions Today | VIP Tips 1.7–2.2 Odds",
        "desc": "Premium Prime Plus football predictions at 1.70–2.20 odds daily. VIP AI football tips with higher long-term value than Prime Safe.",
        "h1": "Prime Plus VIP Football Predictions Today",
        "intro": "Prime Plus targets the 1.70–2.20 value range — offering higher expected long-term returns than Prime Safe while maintaining strong win rates.",
        "markets": ["HOME_WIN","AWAY_WIN","HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW","HOME_OVER_0.5","AWAY_OVER_0.5"],
        "min_conf": 48, "n_tips": 6,
    },
    {
        "slug": "fixed-vip", "key": "FIXED_VIP", "name": "Fixed VIP Tips", "vip": True,
        "title": "Fixed Football Tips Today | VIP Fixed Predictions",
        "desc": "Fixed VIP football predictions — daily AI-selected fixed tips with high win probability. Updated every morning.",
        "h1": "Fixed VIP Football Tips Today",
        "intro": "Fixed VIP tips are our most rigidly filtered selections — match result by margin predictions where our model has strongest conviction.",
        "markets": ["HOME_WIN_BY_1","HOME_WIN_BY_2_PLUS","OVER_0.5"],
        "min_conf": 30, "n_tips": 3,
    },
    {
        "slug": "premium-vip", "key": "PREMIUM_VIP", "name": "Premium VIP Tips", "vip": True,
        "title": "Premium VIP Football Predictions Today | BTTS Win Tips",
        "desc": "Premium VIP football predictions featuring BTTS and win combinations. High-confidence AI tips updated daily.",
        "h1": "Premium VIP Football Predictions Today",
        "intro": "Premium VIP combines win outcomes with BTTS markets — identifying matches where both teams are expected to score AND a winner is likely.",
        "markets": ["HOME_WIN_BTTS","AWAY_WIN_BTTS","OVER_1.5","UNDER_3.5","HOME_WIN_OR_DRAW","AWAY_WIN_OR_DRAW"],
        "min_conf": 48, "n_tips": 5,
    },
    {
        "slug": "single-vip", "key": "SINGLE_VIP", "name": "Single VIP Tip", "vip": True,
        "title": "Best VIP Football Tip Today | Single Premium Prediction",
        "desc": "One premium VIP football tip today — our single highest-confidence AI pick across all markets. Updated daily.",
        "h1": "Best VIP Single Football Tip Today",
        "intro": "The Single VIP tip is our most confident pick of the day — one selection, our strictest confidence filter at 60%+.",
        "markets": ["HOME_OVER_0.5","AWAY_OVER_0.5","UNDER_4.5"],
        "min_conf": 60, "n_tips": 1,
    },
    {
        "slug": "over-under-vip", "key": "OVER_UNDER_VIP", "name": "Over/Under VIP", "vip": True,
        "title": "Over Under VIP Football Tips Today | Goals VIP Predictions",
        "desc": "Premium Over/Under VIP football predictions — high-confidence goals tips across all total goals markets. Updated daily.",
        "h1": "Over Under VIP Football Tips Today",
        "intro": "Over/Under VIP takes our goals market analysis up a level — targeting Over 2.5, Over 3.5 and Under markets where our model has strongest edge.",
        "markets": ["OVER_2.5","OVER_3.5","UNDER_3.5","UNDER_4.5","OVER_1.5"],
        "min_conf": 45, "n_tips": 6,
    },
]

# Quick lookup: slug → category
SLUG_TO_CAT = {c["slug"]: c for c in CATEGORIES}
KEY_TO_CAT  = {c["key"]:  c for c in CATEGORIES}

# ─── Poisson Engine (Python port of index.html §7–§8) ────────────────────────

def clamp(v, lo, hi): return max(lo, min(hi, v))

def _hc(s):
    h = 0
    for ch in (s or ""):
        h = ((h << 5) - h + ord(ch)) & 0xFFFFFFFF
    if h >= 0x80000000: h -= 0x100000000
    return h

def _srand(seed):
    s = [seed & 0xFFFFFFFF]
    def rand():
        s[0] = (s[0] * 1664525 + 1013904223) & 0xFFFFFFFF
        return s[0] / 4294967296.0
    return rand

def noise(seed, id_, range_):
    r = _srand((seed + _hc(id_)) ^ 0xDEADBEEF)
    return math.floor(r() * (range_ * 2 + 1)) - range_

def pmf(k, lam):
    if lam <= 0: return 1.0 if k == 0 else 0.0
    if k < 0: return 0.0
    log_f = 0.0
    for i in range(2, k + 1): log_f += math.log(i)
    return clamp(math.exp(k * math.log(lam) - lam - log_f), 0, 1)

def cdf(n, lam):  return clamp(sum(pmf(i, lam) for i in range(n + 1)), 0, 1)
def ccdf(n, lam): return clamp(1 - cdf(n, lam), 0, 1)
def jp(h, a, lH, lA): return pmf(h, lH) * pmf(a, lA)

def p_home_win(lH, lA):
    p = 0.0
    for h in range(1, 9):
        for a in range(h): p += jp(h, a, lH, lA)
    return clamp(p, 0, 1)

def p_draw(lH, lA):
    return clamp(sum(jp(g, g, lH, lA) for g in range(9)), 0, 1)

def p_away_win(lH, lA):
    p = 0.0
    for a in range(1, 9):
        for h in range(a): p += jp(h, a, lH, lA)
    return clamp(p, 0, 1)

def p_btts(lH, lA):
    return (1 - pmf(0, lH)) * (1 - pmf(0, lA))

def comp_lam(h2h, hCtx, aCtx, rel):
    bH, bA = 1.51, 1.19
    if hCtx and aCtx:
        sH = clamp(hCtx["atk"] * aCtx["def"] * 1.1, 0.2, 5)
        sA = clamp(aCtx["atk"] * hCtx["def"], 0.1, 5)
    else:
        sH, sA = bH, bA
    hH = h2h["hAvg"] if h2h["n"] > 0 else bH
    hA = h2h["aAvg"] if h2h["n"] > 0 else bA
    w = rel * 0.4; sw = 1 - w
    bh = sH * sw + hH * w
    ba = sA * sw + hA * w
    if hCtx: bh *= (1 + hCtx.get("ff", 0))
    if aCtx: ba *= (1 + aCtx.get("ff", 0))
    return clamp(bh, 0.2, 5), clamp(ba, 0.1, 5)

def rel_from_n(n): return [0,.15,.3,.45,.55,.65,.72,.79,.85,.93,1][clamp(n,0,10)]

def calc_h2h(h2h_data):
    ms = []
    if isinstance(h2h_data, dict):
        ms = h2h_data.get("response", {}).get("matches", []) or h2h_data.get("matches", []) or h2h_data.get("data", [])
    base = {"n":0,"hW":0,"aW":0,"dr":0,"avg":2.7,"hAvg":1.51,"aAvg":1.19,"bt":0,"o15":0,"o25":0,"o35":0,"hS":0,"aS":0,"hC":0,"aC":0}
    if not ms: return base
    hW=aW=dr=tG=tH=tA=bt=o1=o2=o3=hs=a_s=hcs=acs=0
    for x in ms:
        h = x.get("home",{}).get("score", x.get("homeScore", x.get("goals",{}).get("home",0))) or 0
        a = x.get("away",{}).get("score", x.get("awayScore", x.get("goals",{}).get("away",0))) or 0
        t = h + a; tG+=t; tH+=h; tA+=a
        if h>a: hW+=1
        elif a>h: aW+=1
        else: dr+=1
        if t>=2: o1+=1
        if t>=3: o2+=1
        if t>=4: o3+=1
        if h>0 and a>0: bt+=1
        if h>0: hs+=1
        if a>0: a_s+=1
        if a==0: hcs+=1
        if h==0: acs+=1
    n = len(ms)
    return {"n":n,"hW":hW,"aW":aW,"dr":dr,"avg":tG/n,"hAvg":tH/n,"aAvg":tA/n,"bt":bt,"o15":o1,"o25":o2,"o35":o3,"hS":hs,"aS":a_s,"hC":hcs,"aC":acs}

def extract_ctx(det, is_home):
    td = None
    if isinstance(det.get("stats"), dict):
        r = det["stats"].get("response") or det["stats"]
        td = r.get("home") if is_home else r.get("away")
    if not td: return None
    s = td.get("stats") or td
    key_w  = "homeWins"  if is_home else "awayWins"
    key_l  = "homeLosses" if is_home else "awayLosses"
    key_d  = "homeDraws"  if is_home else "awayDraws"
    key_gs = "homeGoalsScored"  if is_home else "awayGoalsScored"
    key_gc = "homeGoalsConceded" if is_home else "awayGoalsConceded"
    w = s.get(key_w,0) or 0; l = s.get(key_l,0) or 0; d = s.get(key_d,0) or 0
    gs = s.get(key_gs,0) or 0; gc = s.get(key_gc,0) or 0
    g = max(w+l+d, 1)
    fm = td.get("form","") or s.get("form","") or ""
    rW = fm[-5:].count("W")
    return {"atk": clamp(gs/g,.1,4), "def": clamp(gc/g,.1,4), "wr": clamp(w/g,0,1), "rW": rW, "ff": (rW-2)*0.05}

def extract_imp(det):
    no = {"hW":.4,"dr":.28,"aW":.32,"has":False}
    o = None
    if isinstance(det.get("odds"), dict):
        o = det["odds"].get("response",{}).get("odds") or det["odds"].get("odds") or det["odds"]
    if not o: return no
    rH = float(o.get("home_win") or o.get("homeWin") or o.get("home") or o.get("Home") or o.get("1") or 0)
    rD = float(o.get("draw") or o.get("Draw") or o.get("X") or o.get("x") or 0)
    rA = float(o.get("away_win") or o.get("awayWin") or o.get("away") or o.get("Away") or o.get("2") or 0)
    if rH<=1: rH=0
    if rD<=1: rD=0
    if rA<=1: rA=0
    if not (rH or rD or rA): return no
    iH = 1/rH if rH>1 else 0
    iD = 1/rD if rD>1 else 0
    iA = 1/rA if rA>1 else 0
    s = iH+iD+iA
    if s<=0: return no
    return {"hW":clamp(iH/s,.01,.98),"dr":clamp(iD/s,.01,.98),"aW":clamp(iA/s,.01,.98),"has":True}

def bl(h2s, ps, rel, ip, adv, sn, lo, hi):
    b = h2s * rel + ps * (1 - rel)
    o = b * 0.6 + ip * 100 * 0.4 if ip is not None else b
    return clamp(round(o + (adv or 0) + (sn or 0)), lo, hi)

MARKET_NAMES = {
    "HOME_WIN":"Home Win","AWAY_WIN":"Away Win","DRAW":"Draw",
    "HOME_WIN_OR_DRAW":"Home Win or Draw (1X)","AWAY_WIN_OR_DRAW":"Away Win or Draw (X2)",
    "OVER_0.5":"Over 0.5 Goals","OVER_1.5":"Over 1.5 Goals","OVER_2.5":"Over 2.5 Goals",
    "OVER_3.5":"Over 3.5 Goals","UNDER_2.5":"Under 2.5 Goals","UNDER_3.5":"Under 3.5 Goals",
    "UNDER_4.5":"Under 4.5 Goals","BTTS_YES":"Both Teams to Score","BTTS_NO":"BTTS No",
    "HOME_OVER_0.5":"Home Over 0.5","AWAY_OVER_0.5":"Away Over 0.5",
    "HOME_OVER_1.5":"Home Over 1.5","AWAY_OVER_1.5":"Away Over 1.5",
    "HOME_CLEAN_SHEET":"Home Clean Sheet","AWAY_CLEAN_SHEET":"Away Clean Sheet",
    "HOME_WIN_BTTS":"Home Win & BTTS","AWAY_WIN_BTTS":"Away Win & BTTS",
    "HOME_WIN_OVER_2.5":"Home Win & Over 2.5","AWAY_WIN_OVER_2.5":"Away Win & Over 2.5",
    "HOME_WIN_BY_1":"Home Win by 1","HOME_WIN_BY_2_PLUS":"Home Win by 2+",
    "AWAY_WIN_BY_1":"Away Win by 1","AWAY_WIN_BY_2_PLUS":"Away Win by 2+",
    "EXACT_1_1":"Correct Score: 1-1","EXACT_2_1_HOME":"Correct Score: 2-1",
    "EXACT_3_1_HOME":"Correct Score: 3-1","EXACT_0_1_AWAY":"Correct Score: 0-1",
    "EXACT_0_2_AWAY":"Correct Score: 0-2","EXACT_0_3_AWAY":"Correct Score: 0-3",
    "HT_FT_HOME_HOME":"HT/FT: Home / Home","HT_FT_DRAW_HOME":"HT/FT: Draw / Home",
    "HT_FT_AWAY_AWAY":"HT/FT: Away / Away","HT_FT_DRAW_AWAY":"HT/FT: Draw / Away",
}

def generate_predictions(match, det, markets, min_conf, n_tips):
    """Generate top N predictions for a match filtered to allowed markets."""
    m_id = match.get("id","")
    home_name = match.get("home",{}).get("name","") or match.get("homeTeam",{}).get("name","") or "Home"
    away_name = match.get("away",{}).get("name","") or match.get("awayTeam",{}).get("name","") or "Away"
    sd = (_hc(m_id) ^ (_hc(home_name)*31) ^ (_hc(away_name)*17)) & 0xFFFFFFFF
    if sd >= 0x80000000: sd -= 0x100000000

    h2h  = calc_h2h(det.get("h2h"))
    r    = rel_from_n(h2h["n"])
    ip   = extract_imp(det)
    hCtx = extract_ctx(det, True)
    aCtx = extract_ctx(det, False)
    lH, lA = comp_lam(h2h, hCtx, aCtx, r)
    lT = lH + lA
    t  = max(h2h["n"], 1)

    pHW = p_home_win(lH, lA); pDr = p_draw(lH, lA); pAW = p_away_win(lH, lA)
    hHW = 45 if h2h["n"]==0 else h2h["hW"]/t*100
    hAW = 32 if h2h["n"]==0 else h2h["aW"]/t*100
    hDr = 26 if h2h["n"]==0 else h2h["dr"]/t*100

    def mk(mid, conf):
        return {"id": mid, "name": MARKET_NAMES.get(mid, mid), "confidence": conf,
                "home": home_name, "away": away_name,
                "league": match.get("league",{}).get("name","") or match.get("competition",{}).get("name","") or "",
                "time": match.get("time") or match.get("kickoff",""),
                "match_id": m_id}

    all_preds = {}

    def add(mid, conf):
        if mid in markets and conf >= min_conf:
            all_preds[mid] = mk(mid, conf)

    add("HOME_WIN",           bl(hHW, pHW*100, r, ip["hW"] if ip["has"] else None, 3, noise(sd,"HW",4),36,93))
    add("AWAY_WIN",           bl(hAW, pAW*100, r, ip["aW"] if ip["has"] else None, 0, noise(sd,"AW",4),28,88))
    add("DRAW",               bl(hDr, pDr*100, r, ip["dr"] if ip["has"] else None, 0, noise(sd,"DR",4),24,72))
    h1X = 68 if h2h["n"]==0 else (h2h["hW"]+h2h["dr"])/t*100
    add("HOME_WIN_OR_DRAW",   bl(h1X, (pHW+pDr)*100, r, ip["hW"]+ip["dr"] if ip["has"] else None, 2, noise(sd,"1X",4),40,88))
    hX2 = 57 if h2h["n"]==0 else (h2h["aW"]+h2h["dr"])/t*100
    add("AWAY_WIN_OR_DRAW",   bl(hX2, (pDr+pAW)*100, r, ip["aW"]+ip["dr"] if ip["has"] else None, 0, noise(sd,"X2",4),36,82))

    def gc(pp, hr, id_, lo, hi):
        return bl(hr*100, pp*100, r*0.3, None, 0, noise(sd,id_,5), lo, hi)

    pO15 = ccdf(1,lT); hO15 = .74 if h2h["n"]==0 else h2h["o15"]/t
    add("OVER_1.5",  gc(pO15, hO15, "O15", 55, 93))
    pO25 = ccdf(2,lT); hO25 = .52 if h2h["n"]==0 else h2h["o25"]/t
    add("OVER_2.5",  gc(pO25, hO25, "O25", 34, 88))
    pO35 = ccdf(3,lT); hO35 = .28 if h2h["n"]==0 else h2h["o35"]/t
    add("OVER_3.5",  gc(pO35, hO35, "O35", 22, 76))
    pU25 = cdf(2,lT);  hU25 = .48 if h2h["n"]==0 else (t-h2h["o25"])/t
    add("UNDER_2.5", gc(pU25, hU25, "U25", 28, 86))
    pU35 = cdf(3,lT);  hU35 = .72 if h2h["n"]==0 else (t-h2h["o35"])/t
    add("UNDER_3.5", gc(pU35, hU35, "U35", 42, 92))
    add("UNDER_4.5", clamp(round(cdf(4,lT)*100 + noise(sd,"U45",3)), 68, 96))

    pBt = p_btts(lH,lA); hBt = .48 if h2h["n"]==0 else h2h["bt"]/t
    add("BTTS_YES", gc(pBt, hBt, "BT", 36, 88))
    add("BTTS_NO",  gc(1-pBt, 1-hBt, "BN", 24, 76))

    # Correct score
    for (hg,ag,id_,fl,cl) in [(1,1,"CS11",18,52),(2,1,"CS21",15,48),(3,1,"CS31",12,40),(0,1,"CS01",12,42),(0,2,"CS02",10,36),(0,3,"CS03",10,28)]:
        mid_map = {("CS11","EXACT_1_1"),("CS21","EXACT_2_1_HOME"),("CS31","EXACT_3_1_HOME"),("CS01","EXACT_0_1_AWAY"),("CS02","EXACT_0_2_AWAY"),("CS03","EXACT_0_3_AWAY")}
        mid = next((m for i,m in mid_map if i==id_), None)
        if mid:
            c = clamp(int(jp(hg,ag,lH,lA)*280) + (noise(sd,id_,2) if r>=0.5 and h2h["n"]>=5 else 0), fl, cl)
            add(mid, c)

    # HT/FT
    htL,htA2 = lH*0.45, lA*0.45
    pHtH=p_home_win(htL,htA2); pHtA=p_away_win(htL,htA2); pHtD=p_draw(htL,htA2)
    pFH=p_home_win(lH,lA); pFA=p_away_win(lH,lA)
    add("HT_FT_HOME_HOME", bl(hHW,   pHtH*pFH*100, r, ip["hW"]*0.6 if ip["has"] else None, 0, noise(sd,"HH",6),16,65))
    add("HT_FT_DRAW_HOME", bl((hHW+hDr)/2, pHtD*pFH*100, r, None, 0, noise(sd,"DH",6),12,55))
    add("HT_FT_AWAY_AWAY", bl(hAW,   pHtA*pFA*100, r, ip["aW"]*0.6 if ip["has"] else None, 0, noise(sd,"AA",6),12,60))
    add("HT_FT_DRAW_AWAY", bl((hAW+hDr)/2, pHtD*pFA*100, r, None, 0, noise(sd,"DA",6),10,50))

    # Home/Away scoring
    pHS = 1-pmf(0,lH); pAS = 1-pmf(0,lA)
    hHS = .8 if h2h["n"]==0 else h2h["hS"]/t
    hAS = .72 if h2h["n"]==0 else h2h["aS"]/t
    add("HOME_OVER_0.5", bl(hHS*100, pHS*100, r*0.3, None, 0, noise(sd,"HO5",4), 60,94))
    add("AWAY_OVER_0.5", bl(hAS*100, pAS*100, r*0.3, None, 0, noise(sd,"AO5",4), 54,92))

    # Win+BTTS, Win+O2.5
    hHW2 = .45 if h2h["n"]==0 else h2h["hW"]/t
    hAW2 = .32 if h2h["n"]==0 else h2h["aW"]/t
    hBt2 = .48 if h2h["n"]==0 else h2h["bt"]/t
    hO252 = .52 if h2h["n"]==0 else h2h["o25"]/t
    add("HOME_WIN_BTTS",    bl(hHW2*hBt2*100,  pHW*p_btts(lH,lA)*100, r, ip["hW"]*0.55 if ip["has"] else None, 0, noise(sd,"HWB",5),34,76))
    add("AWAY_WIN_BTTS",    bl(hAW2*hBt2*100,  pAW*p_btts(lH,lA)*100, r, ip["aW"]*0.55 if ip["has"] else None, 0, noise(sd,"AWB",5),28,70))
    add("HOME_WIN_OVER_2.5",bl(hHW2*hO252*100, pHW*ccdf(2,lT)*100,    r, ip["hW"]*0.6  if ip["has"] else None, 0, noise(sd,"HWO",5),30,74))
    add("AWAY_WIN_OVER_2.5",bl(hAW2*hO252*100, pAW*ccdf(2,lT)*100,    r, ip["aW"]*0.6  if ip["has"] else None, 0, noise(sd,"AWO",5),24,70))

    # Win margins
    pW1 = sum(jp(a+1,a,lH,lA) for a in range(9))
    pW2 = sum(jp(hh,a,lH,lA)  for a in range(7) for hh in range(a+2,9))
    pA1 = sum(jp(hh,hh+1,lH,lA) for hh in range(9))
    pA2 = sum(jp(hh,a,lH,lA)  for hh in range(7) for a in range(hh+2,9))
    add("HOME_WIN_BY_1",       bl(hHW2*100*.6, pW1*100, r, None, 0, noise(sd,"W1",5),28,68))
    add("HOME_WIN_BY_2_PLUS",  bl(hHW2*100*.4, pW2*100, r, None, 0, noise(sd,"W2",5),18,64))
    add("AWAY_WIN_BY_1",       bl(hAW2*100*.6, pA1*100, r, None, 0, noise(sd,"A1",5),22,64))
    add("AWAY_WIN_BY_2_PLUS",  bl(hAW2*100*.4, pA2*100, r, None, 0, noise(sd,"A2",5),14,58))

    sorted_preds = sorted(all_preds.values(), key=lambda x: -x["confidence"])
    return sorted_preds[:n_tips]


def pick_tips_for_category(cat, matches, details):
    """Select best N tips across all matches for a category."""
    used_markets = set()
    results = []
    candidates = []
    for m in matches:
        det = details.get(m.get("id",""), {})
        preds = generate_predictions(m, det, set(cat["markets"]), cat["min_conf"], cat["n_tips"])
        for p in preds:
            candidates.append(p)
    candidates.sort(key=lambda x: -x["confidence"])
    for p in candidates:
        if len(results) >= cat["n_tips"]: break
        if p["id"] not in used_markets:
            results.append(p)
            used_markets.add(p["id"])
    return results


# ─── Fetch bundle from API ────────────────────────────────────────────────────

FALLBACK_MATCHES = [
    {"id":"f1","home":{"name":"Arsenal"},"away":{"name":"Chelsea"},"league":{"name":"Premier League"},"time":"15:00"},
    {"id":"f2","home":{"name":"Real Madrid"},"away":{"name":"Barcelona"},"league":{"name":"La Liga"},"time":"20:00"},
    {"id":"f3","home":{"name":"Bayern Munich"},"away":{"name":"Dortmund"},"league":{"name":"Bundesliga"},"time":"17:30"},
    {"id":"f4","home":{"name":"Inter Milan"},"away":{"name":"AC Milan"},"league":{"name":"Serie A"},"time":"19:45"},
    {"id":"f5","home":{"name":"PSG"},"away":{"name":"Marseille"},"league":{"name":"Ligue 1"},"time":"20:00"},
    {"id":"f6","home":{"name":"Man City"},"away":{"name":"Liverpool"},"league":{"name":"Premier League"},"time":"16:30"},
    {"id":"f7","home":{"name":"Atletico Madrid"},"away":{"name":"Sevilla"},"league":{"name":"La Liga"},"time":"20:00"},
    {"id":"f8","home":{"name":"Juventus"},"away":{"name":"Napoli"},"league":{"name":"Serie A"},"time":"18:00"},
    {"id":"f9","home":{"name":"Ajax"},"away":{"name":"PSV"},"league":{"name":"Eredivisie"},"time":"14:30"},
    {"id":"f10","home":{"name":"Porto"},"away":{"name":"Benfica"},"league":{"name":"Primeira Liga"},"time":"21:00"},
]

def fetch_bundle():
    print(f"  Fetching {API_URL} ...")
    try:
        req = urllib.request.Request(API_URL, headers={"User-Agent":"SafeOdds-SEO-Bot/2.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = json.loads(r.read().decode())
        if raw.get("status") == "error": raise Exception("API returned error")
        ms = (raw.get("response",{}).get("matches") or raw.get("matches") or
              raw.get("data",{}).get("matches") if isinstance(raw.get("data"),dict) else None or
              raw.get("fixtures") or [])
        if not isinstance(ms, list): ms = []
        details = {}
        for m in ms:
            mid = m.get("id") or m.get("fixture",{}).get("id") or ("m"+hashlib.md5(str(m).encode()).hexdigest()[:8])
            m["id"] = str(mid)
            details[str(mid)] = {
                "h2h":  m.get("cachedH2H") or m.get("h2h"),
                "stats":m.get("cachedStats") or m.get("stats"),
                "odds": m.get("cachedOdds") or m.get("odds"),
            }
        print(f"  ✓ {len(ms)} matches loaded")
        return ms, details
    except Exception as e:
        print(f"  ⚠ API error: {e} — using fallback data")
        return FALLBACK_MATCHES, {m["id"]:{} for m in FALLBACK_MATCHES}


# ─── HTML Templates ───────────────────────────────────────────────────────────

LOGO_SVG = "<svg viewBox='0 0 32 32' fill='none'><circle cx='16' cy='16' r='15' stroke='#00c853' stroke-width='2'/><path d='M16 4a12 12 0 110 24 12 12 0 010-24zm0 3a9 9 0 100 18 9 9 0 000-18z' fill='#00c853' opacity='.3'/><path d='M10 16h12M16 10v12' stroke='#00c853' stroke-width='1.2' opacity='.5'/><circle cx='16' cy='16' r='3' fill='#00c853'/></svg>"

ALL_NAV_LINKS = [
    ("prime-safe","Prime Safe"),("daily-5-odds","5 Odds"),("daily-10-odds","10 Odds"),
    ("over-under","Over/Under"),("correct-score","Correct Score"),("ht-ft-vip","HT/FT"),
    ("50-plus-odds","50+ Odds"),("about","About"),
]

SHARED_CSS = """*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0d1117;--card:#161b22;--card2:#1c2333;--accent:#00c853;--accent2:#00e676;--text:#e6edf3;--text2:#8b949e;--border:#30363d;--red:#f85149;--gold:#f0b429;--vip:#ff6d00}
html{scroll-behavior:smooth}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.hdr{background:#010409;border-bottom:2px solid var(--accent);padding:12px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;position:sticky;top:0;z-index:100;backdrop-filter:blur(12px)}
.logo{display:flex;align-items:center;gap:8px;text-decoration:none}
.logo svg{width:32px;height:32px;flex-shrink:0}
.logo span{font-size:18px;font-weight:800;color:var(--text)}.logo span em{color:var(--accent);font-style:normal}
.nav{display:flex;gap:14px;flex-wrap:wrap}.nav a{font-size:12px;color:var(--text2);transition:.2s}.nav a:hover,.nav a.active{color:var(--accent);text-decoration:none}
.rg-bar{background:rgba(240,180,41,.08);border-bottom:1px solid rgba(240,180,41,.2);padding:8px 20px;font-size:11px;color:var(--text2);display:flex;align-items:center;gap:8px}
.rg-bar a{color:var(--gold);text-decoration:underline}.rg-bar strong{color:var(--gold)}
.hero{background:linear-gradient(135deg,#0d1117,#161b22);border-bottom:1px solid var(--border);padding:44px 20px 36px;text-align:center}
.hero h1{font-size:clamp(20px,5vw,32px);font-weight:800;line-height:1.2;margin-bottom:12px}.hero h1 em{color:var(--accent);font-style:normal}
.hero p{font-size:14px;color:var(--text2);max-width:580px;margin:0 auto 22px;line-height:1.7}
.badge-row{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-bottom:26px}
.badge{padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;border:1px solid}
.badge.green{border-color:rgba(0,200,83,.4);color:var(--accent);background:rgba(0,200,83,.08)}
.badge.gold{border-color:rgba(240,180,41,.4);color:var(--gold);background:rgba(240,180,41,.08)}
.badge.vip{border-color:rgba(255,109,0,.4);color:var(--vip);background:rgba(255,109,0,.08)}
.cta-btn{display:inline-block;padding:13px 30px;background:var(--accent);color:#000;border-radius:10px;font-weight:700;font-size:14px;transition:.2s}.cta-btn:hover{background:var(--accent2);text-decoration:none}
.breadcrumb{font-size:12px;color:var(--text2);padding:9px 20px;background:var(--card);border-bottom:1px solid var(--border)}
.breadcrumb a{color:var(--text2)}.breadcrumb a:hover{color:var(--accent)}
.container{max-width:820px;margin:0 auto;padding:30px 20px}
.section{margin-bottom:38px}
.section-title{font-size:17px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.tips-grid{display:grid;gap:10px}
.tip-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;transition:.2s}
.tip-card:hover{border-color:rgba(0,200,83,.35)}
.tip-meta{flex:1;min-width:0}
.tip-match{font-size:14px;font-weight:700;margin-bottom:3px}
.tip-league{font-size:11px;color:var(--text2)}
.tip-time{font-size:11px;color:var(--text2);margin-top:2px}
.tip-right{display:flex;flex-direction:column;align-items:flex-end;gap:5px;flex-shrink:0}
.tip-pick{background:rgba(0,200,83,.1);border:1px solid rgba(0,200,83,.3);color:var(--accent);padding:5px 12px;border-radius:8px;font-size:12px;font-weight:700;white-space:nowrap}
.tip-pick.blurred{filter:blur(5px);user-select:none;background:rgba(255,109,0,.1);border-color:rgba(255,109,0,.3);color:var(--vip);cursor:pointer}
.tip-conf{font-size:11px;color:var(--text2)}
.conf-bar-wrap{width:80px;height:4px;background:var(--border);border-radius:2px;overflow:hidden;margin-top:3px}
.conf-bar{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.vip-notice{background:rgba(255,109,0,.08);border:1px solid rgba(255,109,0,.25);border-radius:10px;padding:14px 16px;text-align:center;margin-top:14px}
.vip-notice p{font-size:13px;color:var(--text2);margin-bottom:8px}
.vip-notice a{display:inline-block;padding:9px 22px;background:var(--vip);color:#fff;border-radius:8px;font-size:13px;font-weight:700;text-decoration:none}
.archive-list{list-style:none;display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.archive-list li a{display:inline-block;padding:5px 12px;background:var(--card);border:1px solid var(--border);border-radius:8px;font-size:12px;color:var(--text2);transition:.2s}
.archive-list li a:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}
.info-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:14px}
.info-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}
.info-card h3{font-size:13px;font-weight:700;color:var(--accent);margin-bottom:6px}
.info-card p{font-size:13px;color:var(--text2);line-height:1.6}
.links-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:10px;margin-top:14px}
.link-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px;text-align:center;display:block;transition:.2s}
.link-card:hover{border-color:var(--accent);text-decoration:none}
.link-card strong{display:block;font-size:12px;color:var(--text);margin-bottom:2px}
.link-card span{font-size:11px;color:var(--text2)}
.link-card.vip-link span{color:var(--vip)}
.disclaimer{background:rgba(248,81,73,.05);border:1px solid rgba(248,81,73,.2);border-radius:10px;padding:13px 16px;font-size:12px;color:var(--text2);margin-top:30px;line-height:1.7}
.disclaimer strong{color:var(--red)}
.disclaimer a{color:var(--text2);text-decoration:underline}
.ft{text-align:center;padding:28px 20px;color:var(--text2);font-size:12px;border-top:1px solid var(--border)}
.ft a{color:var(--text2);margin:0 8px}.ft a:hover{color:var(--accent)}
@media(max-width:500px){.hero{padding:30px 16px 28px}.container{padding:22px 14px}.tip-card{flex-direction:column;align-items:flex-start}.tip-right{flex-direction:row;align-items:center;width:100%;justify-content:space-between}}"""

def build_nav(active_slug=""):
    links = "".join(
        f'<a href="/{s}/" class="{"active" if s==active_slug else ""}">{n}</a>'
        for s,n in ALL_NAV_LINKS
    )
    return f'<header class="hdr"><a href="/" class="logo">{LOGO_SVG}<span>Safe<em>Odds</em></span></a><nav class="nav">{links}</nav></header>'

def build_footer():
    return """<footer class="ft">
  <p>© 2026 SafeOddsFootballTips.com · AI Football Predictions</p>
  <p style="margin-top:8px"><a href="/">Home</a><a href="/about/">About</a><a href="/how-it-works/">How It Works</a><a href="/contact/">Contact</a></p>
  <p style="margin-top:10px;font-size:11px;opacity:.6">For entertainment purposes only. Please gamble responsibly. 18+ only.</p>
</footer>"""

def build_rg_bar():
    return '<div class="rg-bar">⚠️ <strong>Bet Responsibly.</strong>&nbsp;Predictions are for information only. Only bet what you can afford to lose. Help: <a href="https://www.begambleaware.org" rel="nofollow" target="_blank">BeGambleAware.org</a></div>'

def build_disclaimer():
    return '<div class="disclaimer"><strong>⚠ Responsible Gambling:</strong> These predictions are for entertainment and informational purposes only. Football betting involves risk — never bet more than you can afford to lose. If gambling is affecting your life, seek help at <a href="https://www.begambleaware.org" rel="nofollow">BeGambleAware.org</a> or call 0808 8020 133. 18+ only.</div>'

def build_internal_links(exclude_slug=""):
    items = ""
    for cat in CATEGORIES:
        if cat["slug"] == exclude_slug: continue
        vip_cls = ' vip-link' if cat["vip"] else ''
        label = "VIP Tips" if cat["vip"] else "Free Tips"
        items += f'<a href="/{cat["slug"]}/" class="link-card{vip_cls}"><strong>{cat["name"]}</strong><span>{label}</span></a>'
    return f'<div class="links-grid">{items}</div>'

def build_tips_html(tips, is_vip):
    if not tips:
        return '<p style="color:var(--text2);padding:16px 0">No predictions met the confidence threshold for today. Check back tomorrow.</p>'
    html = ""
    for p in tips:
        pick_cls = "tip-pick blurred" if is_vip else "tip-pick"
        pick_title = 'title="Unlock VIP to see this prediction" onclick="document.getElementById(\'vip-cta\').scrollIntoView({behavior:\'smooth\'})"' if is_vip else ''
        conf = p["confidence"]
        conf_color = "var(--accent)" if conf >= 65 else ("var(--gold)" if conf >= 45 else "var(--red)")
        html += f"""<div class="tip-card">
  <div class="tip-meta">
    <div class="tip-match">{p['home']} vs {p['away']}</div>
    <div class="tip-league">{p['league']}</div>
    {'<div class="tip-time">🕐 '+p['time']+'</div>' if p.get('time') else ''}
  </div>
  <div class="tip-right">
    <div class="{pick_cls}" {pick_title}>{'🔒 VIP Tip' if is_vip else '🎯 '+p['name']}</div>
    <div class="tip-conf" style="color:{conf_color}">Confidence: {conf}%</div>
    <div class="conf-bar-wrap"><div class="conf-bar" style="width:{conf}%;background:{conf_color}"></div></div>
  </div>
</div>"""
    return html

def build_schema(cat, url, is_dated=False):
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": f"{cat['title']} | SafeOdds",
        "description": cat["desc"],
        "url": url,
        "datePublished": TODAY_ISO,
        "dateModified": TODAY_ISO,
        "publisher": {
            "@type": "Organization",
            "name": "Safe Odds Football Tips",
            "url": DOMAIN,
            "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/favicon.ico"}
        },
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type":"ListItem","position":1,"name":"Home","item":DOMAIN+"/"},
                {"@type":"ListItem","position":2,"name":cat["name"],"item":f"{DOMAIN}/{cat['slug']}/"},
            ] + ([{"@type":"ListItem","position":3,"name":TODAY_STR,"item":url}] if is_dated else [])
        }
    }
    return json.dumps(schema, separators=(",",":"))


def build_base_page(cat, tips):
    """The live base page — regenerated daily, always shows today's predictions."""
    base_url   = f"{DOMAIN}/{cat['slug']}/"
    dated_url  = f"{DOMAIN}/{cat['slug']}/{TODAY_SLUG}/"
    canonical  = base_url
    tips_html  = build_tips_html(tips, cat["vip"])
    vip_section = ""
    if cat["vip"]:
        vip_section = f"""<div class="vip-notice" id="vip-cta">
  <p>🔒 Full predictions are available in the SafeOdds VIP app. Unlock {cat['name']} to see all tips.</p>
  <a href="/?cat={cat['key']}#unlock">Unlock {cat['name']} VIP →</a>
</div>"""

    # Archive links — today's dated page
    archive_html = f'<ul class="archive-list"><li><a href="{dated_url}">📅 {TODAY_STR} (today)</a></li></ul>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{cat['title']} | SafeOdds</title>
<meta name="description" content="{cat['desc']}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{cat['title']} | SafeOdds">
<meta property="og:description" content="{cat['desc']}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Safe Odds Football Tips">
<meta name="robots" content="index, follow">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%23111' stroke='%2300c853' stroke-width='2'/><circle cx='16' cy='16' r='3' fill='%2300c853'/></svg>">
<script type="application/ld+json">{build_schema(cat, canonical, False)}</script>
<style>{SHARED_CSS}</style>
</head>
<body>
{build_nav(cat['slug'])}
{build_rg_bar()}
<div class="breadcrumb"><a href="/">Home</a> › {cat['name']}</div>
<section class="hero">
  <h1>⚽ <em>{cat['h1']}</em></h1>
  <p>{cat['intro']}</p>
  <div class="badge-row">
    <span class="badge green">Updated {TODAY_STR}</span>
    <span class="badge gold">AI-Powered</span>
    {'<span class="badge vip">VIP</span>' if cat['vip'] else '<span class="badge green">Free Tips</span>'}
  </div>
  <a href="/" class="cta-btn">Open Live App →</a>
</section>
<div class="container">
  <section class="section">
    <h2 class="section-title">📅 {cat['name']} Predictions — {TODAY_STR}</h2>
    <div class="tips-grid">{tips_html}</div>
    {vip_section}
    <p style="margin-top:12px;font-size:12px;color:var(--text2)">
      Full live predictions in the <a href="/">SafeOdds app</a>. 
      See archived predictions: {archive_html}
    </p>
  </section>
  <section class="section">
    <h2 class="section-title">ℹ️ About {cat['name']}</h2>
    <p style="font-size:14px;color:var(--text2);line-height:1.8">{cat['intro']} Our AI fetches live fixtures, odds, head-to-head stats and team form every morning and runs a Poisson probability model to identify the highest-confidence picks.</p>
  </section>
  <section class="section">
    <h2 class="section-title">🔗 More Football Tips Today</h2>
    {build_internal_links(cat['slug'])}
  </section>
  {build_disclaimer()}
</div>
{build_footer()}
</body></html>"""


def build_dated_page(cat, tips, archive_links=""):
    """The static dated snapshot — permanently archived, never changes after generation."""
    base_url  = f"{DOMAIN}/{cat['slug']}/"
    dated_url = f"{DOMAIN}/{cat['slug']}/{TODAY_SLUG}/"
    canonical = dated_url
    tips_html = build_tips_html(tips, cat["vip"])
    vip_section = ""
    if cat["vip"]:
        vip_section = f"""<div class="vip-notice">
  <p>🔒 This is a preview. Full predictions available in the SafeOdds VIP app.</p>
  <a href="/?cat={cat['key']}#unlock">Unlock {cat['name']} VIP →</a>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{cat['name']} Predictions {TODAY_STR} | SafeOdds</title>
<meta name="description" content="{cat['name']} football predictions for {TODAY_STR}. {cat['desc']}">
<link rel="canonical" href="{canonical}">
<link rel="prev" href="{base_url}">
<meta property="og:title" content="{cat['name']} Predictions {TODAY_STR} | SafeOdds">
<meta property="og:description" content="{cat['name']} football tips for {TODAY_STR}.">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Safe Odds Football Tips">
<meta name="robots" content="index, follow">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='%23111' stroke='%2300c853' stroke-width='2'/><circle cx='16' cy='16' r='3' fill='%2300c853'/></svg>">
<script type="application/ld+json">{build_schema(cat, canonical, True)}</script>
<style>{SHARED_CSS}</style>
</head>
<body>
{build_nav()}
{build_rg_bar()}
<div class="breadcrumb"><a href="/">Home</a> › <a href="{base_url}">{cat['name']}</a> › {TODAY_STR}</div>
<section class="hero">
  <h1>⚽ <em>{cat['name']} Predictions</em></h1>
  <p style="font-size:16px;font-weight:700;color:var(--accent);margin-bottom:8px">{TODAY_STR}</p>
  <p>{cat['intro']}</p>
  <div class="badge-row">
    <span class="badge green">📅 {TODAY_STR}</span>
    <span class="badge gold">AI-Powered</span>
    {'<span class="badge vip">VIP</span>' if cat['vip'] else '<span class="badge green">Free Tips</span>'}
  </div>
  <a href="/{cat['slug']}/" class="cta-btn">See Today's Latest Tips →</a>
</section>
<div class="container">
  <section class="section">
    <h2 class="section-title">🎯 {cat['name']} Predictions — {TODAY_STR}</h2>
    <div class="tips-grid">{tips_html}</div>
    {vip_section}
  </section>
  <section class="section">
    <h2 class="section-title">🔗 More Football Tips Today</h2>
    {build_internal_links(cat['slug'])}
  </section>
  {build_disclaimer()}
</div>
{build_footer()}
</body></html>"""


# ─── Sitemap updater ──────────────────────────────────────────────────────────

SITEMAP_STATIC_URLS = [
    (f"{DOMAIN}/",              "daily",   "1.0"),
] + [
    (f"{DOMAIN}/{c['slug']}/",  "daily",   "0.9") for c in CATEGORIES
] + [
    (f"{DOMAIN}/about/",        "monthly", "0.5"),
    (f"{DOMAIN}/how-it-works/", "monthly", "0.5"),
    (f"{DOMAIN}/contact/",      "monthly", "0.4"),
]

def rebuild_sitemap(dated_urls):
    """Rebuild sitemap: static pages + all dated pages accumulated over time."""
    path = os.path.join(BASE, "sitemap.xml")

    # Read existing dated URLs from sitemap to preserve history
    existing_dated = set()
    if os.path.exists(path):
        content = open(path).read()
        import re
        for m in re.finditer(r'<loc>(https?://[^<]+/\d{4}-\d{2}-\d{2}/)</loc>', content):
            existing_dated.add(m.group(1))

    # Add today's new dated URLs
    for u in dated_urls:
        existing_dated.add(u)

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    # Static pages
    for url, freq, pri in SITEMAP_STATIC_URLS:
        lines.append(f'  <url><loc>{url}</loc><lastmod>{TODAY_ISO}</lastmod><changefreq>{freq}</changefreq><priority>{pri}</priority></url>')

    # All dated pages (historical + today)
    for url in sorted(existing_dated, reverse=True):
        date_part = url.rstrip("/").split("/")[-1]
        lines.append(f'  <url><loc>{url}</loc><lastmod>{date_part}</lastmod><changefreq>never</changefreq><priority>0.7</priority></url>')

    lines.append('</urlset>')
    open(path, "w").write("\n".join(lines))
    print(f"  ✓ Sitemap rebuilt — {len(SITEMAP_STATIC_URLS)} static + {len(existing_dated)} dated URLs")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🚀 SafeOdds Daily Generator v2 — {TODAY_STR}\n")

    # 1. Fetch live bundle
    matches, details = fetch_bundle()
    print(f"  Using {len(matches)} matches\n")

    dated_urls = []

    for cat in CATEGORIES:
        slug = cat["slug"]

        # 2. Run prediction engine for this category
        tips = pick_tips_for_category(cat, matches, details)
        print(f"  [{slug}] {len(tips)} tips generated")

        # 3. Build & write base page (always overwrite — stays fresh)
        base_dir  = os.path.join(BASE, slug)
        base_file = os.path.join(base_dir, "index.html")
        os.makedirs(base_dir, exist_ok=True)
        open(base_file, "w", encoding="utf-8").write(build_base_page(cat, tips))
        print(f"  ✓ /{slug}/index.html (base)")

        # 4. Build & write dated snapshot page
        dated_dir  = os.path.join(BASE, slug, TODAY_SLUG)
        dated_file = os.path.join(dated_dir, "index.html")
        dated_url  = f"{DOMAIN}/{slug}/{TODAY_SLUG}/"
        os.makedirs(dated_dir, exist_ok=True)
        open(dated_file, "w", encoding="utf-8").write(build_dated_page(cat, tips))
        print(f"  ✓ /{slug}/{TODAY_SLUG}/index.html (dated)")
        dated_urls.append(dated_url)

    # 5. Rebuild sitemap
    print()
    rebuild_sitemap(dated_urls)
    print(f"\n✅ Done — {len(CATEGORIES)} categories × 2 pages = {len(CATEGORIES)*2} HTML files for {TODAY_STR}\n")

if __name__ == "__main__":
    main()
