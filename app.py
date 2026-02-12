import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
import os
import urllib.parse

APP_TITLE = "Shipping Execution — $1.1M Plan (Desktop)"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

TARGETS_PATH = os.path.join(DATA_DIR, "targets.json")
TOUCHES_PATH = os.path.join(DATA_DIR, "touches.json")
TEMPLATES_PATH = os.path.join(DATA_DIR, "templates.json")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

DEFAULT_TARGET_VALUE = 15000
REVENUE_TARGET_DEFAULT = 1_100_000

CADENCE = [
    ("Email 1 — Intro", 0,  "EMAIL_1_INTRO"),
    ("Email 2 — Bump", 2,  "EMAIL_2_BUMP"),
    ("LinkedIn — Connect", 5, "LINKEDIN_CONNECT"),
    ("Email 3 — Value", 7, "EMAIL_3_VALUE"),
    ("Email 4 — Social Proof", 10, "EMAIL_4_SOCIAL"),
    ("Email 5 — Right Person", 13, "EMAIL_5_RIGHT_PERSON"),
    ("Email 6 — Close Loop", 17, "EMAIL_6_CLOSE"),
    ("Recycle — Q4", 45, "RECYCLE_Q4"),
]

DEFAULT_TEMPLATES = {
    "EMAIL_1_INTRO": {
        "subject": "Quick question re: client gifting this year",
        "body": """Hi {{FirstName}} — I’m Chris with Jack Stack Barbecue here in KC.

We help KC firms run client/partner gifting programs that feel premium and are simple to execute — especially ahead of Q4.

Quick question: who’s the right person on your team to coordinate gifting and vendor selection?

Thanks,
Chris"""
    },
    "EMAIL_2_BUMP": {
        "subject": "Re: Quick question",
        "body": """Hi {{FirstName}} — just bumping this in case it got buried.

Is there someone else I should reach out to for gifting/vendor coordination?

Thanks,
Chris"""
    },
    "EMAIL_3_VALUE": {
        "subject": "Simple way we support Q4 gifting",
        "body": """Hi {{FirstName}} — if helpful, I can send a 1-page overview with pricing bands and a few common corporate programs we run for KC firms.

Want that?

Chris"""
    },
    "EMAIL_4_SOCIAL": {
        "subject": "KC firms using gifting as a relationship tool",
        "body": """Hi {{FirstName}} — we’ve found the best corporate gifting programs do two things:
1) protect key relationships, and
2) make execution simple for the team.

If you’re the right person, happy to share what’s working. If not, who owns this?

Chris"""
    },
    "EMAIL_5_RIGHT_PERSON": {
        "subject": "Closing the loop",
        "body": """Hi {{FirstName}} — last quick note from me.

Should I be speaking with Marketing, an EA, or Client Experience for gifting coordination?

Thanks,
Chris"""
    },
    "EMAIL_6_CLOSE": {
        "subject": "I’ll close this out for now",
        "body": """Hi {{FirstName}} — I’m going to close this out to avoid clutter.

If you want, I can circle back in early September (planning) or early November (execution). Which is better?

Chris"""
    },
    "RECYCLE_Q4": {
        "subject": "Quick check-in for Q4 gifting",
        "body": """Hi {{FirstName}} — checking in as teams start planning Q4 gifting.

Do you want me to send over a quick menu with pricing bands and lead times?

Chris"""
    }
}

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def business_days_add(d: date, days: int) -> date:
    step = 1 if days >= 0 else -1
    remaining = abs(days)
    cur = d
    while remaining > 0:
        cur = cur + timedelta(days=step)
        while cur.weekday() >= 5:  # Sat/Sun
            cur = cur + timedelta(days=step)
        remaining -= 1
    return cur

def first_name(full: str) -> str:
    if not full:
        return ""
    return full.strip().split()[0]

def interpolate(text: str, target: dict) -> str:
    return (text
        .replace("{{FirstName}}", first_name(target.get("contact_name","")))
        .replace("{{Company}}", target.get("company",""))
        .replace("{{YourName}}", "Chris")
    )

def mailto_link(to: str, subject: str, body: str) -> str:
    # mailto opens default mail client (set Outlook as default)
    q = {
        "subject": subject,
        "body": body
    }
    return f"mailto:{urllib.parse.quote(to)}?{urllib.parse.urlencode(q, quote_via=urllib.parse.quote)}"

def next_action(target: dict, touches: list, start_date: date) -> dict | None:
    sent = {t["action"] for t in touches if t["target_id"] == target["id"]}
    # start reference: first touch date or chosen start_date
    first_touch = None
    for t in sorted([t for t in touches if t["target_id"] == target["id"]], key=lambda x: x["date"]):
        first_touch = datetime.fromisoformat(t["date"]).date()
        break
    base = first_touch or start_date

    for label, offset, code in CADENCE:
        if code not in sent:
            due = business_days_add(base, offset)
            return {"label": label, "offset": offset, "action": code, "due": due}
    return None

def due_today(targets, touches, start_date: date):
    today = date.today()
    items = []
    for t in targets:
        na = next_action(t, touches, start_date)
        if na and na["due"] <= today:
            items.append((na["due"], t, na))
    items.sort(key=lambda x: x[0])
    return items

def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

def calc_metrics(targets, touches, start_date: date, revenue_target: float):
    started_ids = set([t["target_id"] for t in touches])
    projected = sum([t.get("estimated_value", DEFAULT_TARGET_VALUE) for t in targets if t["id"] in started_ids])
    # secured: user-marked wins
    secured = sum([t.get("actual_value", 0) for t in targets if t.get("status") == "WON"])
    gap = max(revenue_target - secured, 0)

    ws = week_start(date.today())
    this_week_touches = [t for t in touches if datetime.fromisoformat(t["date"]).date() >= ws]
    intros = [t for t in this_week_touches if t["action"] == "EMAIL_1_INTRO"]

    return {
        "secured": secured,
        "projected": projected,
        "gap": gap,
        "due_today": len(due_today(targets, touches, start_date)),
        "touches_week": len(this_week_touches),
        "intros_week": len(intros),
    }

# ---- App ----
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("Review-first cadence tool. Designed for Windows + Outlook. Stores data locally in ./data")

settings = load_json(SETTINGS_PATH, {"revenue_target": REVENUE_TARGET_DEFAULT, "cadence_start": str(date.today())})
templates = load_json(TEMPLATES_PATH, DEFAULT_TEMPLATES)
targets = load_json(TARGETS_PATH, [])
touches = load_json(TOUCHES_PATH, [])

start_date = date.fromisoformat(settings.get("cadence_start", str(date.today())))
revenue_target = float(settings.get("revenue_target", REVENUE_TARGET_DEFAULT))

with st.sidebar:
    st.header("Settings")
    revenue_target = st.number_input("Revenue target", min_value=0.0, value=float(revenue_target), step=10000.0)
    start_date = st.date_input("Cadence start date", value=start_date)
    if st.button("Save settings"):
        settings["revenue_target"] = revenue_target
        settings["cadence_start"] = str(start_date)
        save_json(SETTINGS_PATH, settings)
        st.success("Saved.")

    st.divider()
    st.header("Import")
    up = st.file_uploader("Upload Targets (Excel or CSV)", type=["xlsx","csv"])
    if up is not None:
        if up.name.lower().endswith(".csv"):
            df = pd.read_csv(up)
        else:
            df = pd.read_excel(up)
        # normalize
        def col(name):
            for c in df.columns:
                if str(c).strip().lower() == name:
                    return c
            return None

        company_c = col("company")
        domain_c = col("domain")
        role_c = col("target role")
        contact_c = col("contact name")
        email_c = col("email / pattern") or col("email pattern") or col("email")

        if company_c is None or domain_c is None:
            st.error("Missing required columns: Company, Domain")
        else:
            imported = 0
            for _, r in df.iterrows():
                company = str(r[company_c]).strip()
                domain = str(r[domain_c]).strip()
                if not company or company.lower()=="nan": 
                    continue
                # merge key
                key = (company.lower(), domain.lower())
                existing = next((t for t in targets if (t["company"].lower(), t["domain"].lower()) == key), None)
                if existing is None:
                    existing = {
                        "id": f"{company.lower()}::{domain.lower()}",
                        "company": company,
                        "domain": domain,
                        "contact_name": "",
                        "role": "",
                        "email": "",
                        "tier": "B",
                        "status": "NOT_CONTACTED",
                        "estimated_value": DEFAULT_TARGET_VALUE,
                        "actual_value": 0,
                        "notes": ""
                    }
                    targets.append(existing)

                if contact_c is not None:
                    v = str(r[contact_c]).strip()
                    if v and v.lower() != "nan" and not existing["contact_name"]:
                        existing["contact_name"] = v
                if role_c is not None:
                    v = str(r[role_c]).strip()
                    if v and v.lower() != "nan" and not existing["role"]:
                        existing["role"] = v
                if email_c is not None:
                    v = str(r[email_c]).strip()
                    if v and v.lower() != "nan" and not existing["email"]:
                        existing["email"] = v

                imported += 1

            save_json(TARGETS_PATH, targets)
            st.success(f"Imported/merged {imported} rows into {len(targets)} targets.")

tabs = st.tabs(["Dashboard","Targets","Templates","Export"])

# ---- Dashboard ----
with tabs[0]:
    m = calc_metrics(targets, touches, start_date, revenue_target)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Target", f"${revenue_target:,.0f}")
    c2.metric("Secured", f"${m['secured']:,.0f}")
    c3.metric("Projected", f"${m['projected']:,.0f}")
    c4.metric("Due Today", m["due_today"])

    st.divider()
    st.subheader("Due Today")
    items = due_today(targets, touches, start_date)
    if not items:
        st.write("Nothing due today.")
    else:
        for due, t, na in items:
            with st.container(border=True):
                cols = st.columns([3,2,2,2])
                cols[0].markdown(f"**{t['company']}**  \n{t['domain']}")
                cols[1].write(na["label"])
                cols[2].write(f"Due {due.strftime('%b %d')}")
                if cols[3].button("Open", key=f"open_{t['id']}"):
                    st.session_state["open_target_id"] = t["id"]
                    st.switch_page("app.py")  # no-op in single page

# ---- Targets ----
with tabs[1]:
    st.subheader("Targets")
    if "open_target_id" not in st.session_state:
        st.session_state["open_target_id"] = None

    # filters
    q = st.text_input("Search", "")
    fcol1, fcol2, fcol3 = st.columns(3)
    tier_filter = fcol1.selectbox("Tier", ["All","A","B","C"])
    status_filter = fcol2.selectbox("Status", ["All","NOT_CONTACTED","IN_PLAY","ENGAGED","MEETING","PROPOSAL","WON","LOST"])
    show_due_only = fcol3.checkbox("Due only", value=False)

    filtered = targets
    if q.strip():
        filtered = [t for t in filtered if q.lower() in t["company"].lower()]
    if tier_filter != "All":
        filtered = [t for t in filtered if t.get("tier","B") == tier_filter]
    if status_filter != "All":
        filtered = [t for t in filtered if t.get("status","NOT_CONTACTED") == status_filter]
    if show_due_only:
        def is_due(t):
            na = next_action(t, touches, start_date)
            return na and na["due"] <= date.today()
        filtered = [t for t in filtered if is_due(t)]

    # sort by next due
    def sort_key(t):
        na = next_action(t, touches, start_date)
        return na["due"] if na else date.max
    filtered = sorted(filtered, key=sort_key)

    # selection
    names = [f"{t['company']} ({t.get('tier','B')})" for t in filtered]
    idx = st.selectbox("Select target", range(len(filtered)) if filtered else [], format_func=lambda i: names[i] if filtered else "")
    if filtered:
        t = filtered[idx]
        na = next_action(t, touches, start_date)

        left, right = st.columns([2,1])
        with left:
            st.markdown(f"## {t['company']}")
            st.write(t["domain"])
            t["contact_name"] = st.text_input("Contact name", t.get("contact_name",""))
            t["role"] = st.text_input("Role", t.get("role",""))
            t["email"] = st.text_input("Email (or pattern)", t.get("email",""))
            t["tier"] = st.selectbox("Tier", ["A","B","C"], index=["A","B","C"].index(t.get("tier","B")))
            t["status"] = st.selectbox("Status", ["NOT_CONTACTED","IN_PLAY","ENGAGED","MEETING","PROPOSAL","WON","LOST"], index=["NOT_CONTACTED","IN_PLAY","ENGAGED","MEETING","PROPOSAL","WON","LOST"].index(t.get("status","NOT_CONTACTED")))
            t["estimated_value"] = st.number_input("Estimated value", value=float(t.get("estimated_value",DEFAULT_TARGET_VALUE)), step=1000.0)
            t["actual_value"] = st.number_input("Actual value (if Won)", value=float(t.get("actual_value",0)), step=1000.0)
            t["notes"] = st.text_area("Notes", t.get("notes",""), height=120)

            if st.button("Save target"):
                save_json(TARGETS_PATH, targets)
                st.success("Saved.")

        with right:
            st.markdown("### Next Action")
            if na:
                st.write(na["label"])
                st.write(f"Due: {na['due'].strftime('%b %d, %Y')}")
                if na["action"].startswith("EMAIL"):
                    tpl = templates.get(na["action"], {"subject":"", "body":""})
                    subject = interpolate(tpl["subject"], t)
                    body = interpolate(tpl["body"], t)

                    st.markdown("#### Review")
                    subject_edit = st.text_input("Subject", subject, key=f"sub_{t['id']}_{na['action']}")
                    body_edit = st.text_area("Body", body, height=220, key=f"body_{t['id']}_{na['action']}")

                    to_addr = t.get("email","").strip() or ""
                    if not to_addr or "@" not in to_addr:
                        st.warning("No valid email address set. Add email (not just pattern) to open Outlook compose.")
                    else:
                        link = mailto_link(to_addr, subject_edit, body_edit)
                        st.link_button("Open in Outlook (review-first)", link)

                    if st.button("Mark Sent (log touch)", key=f"sent_{t['id']}_{na['action']}"):
                        touches.append({
                            "target_id": t["id"],
                            "action": na["action"],
                            "date": datetime.now().isoformat(timespec="seconds")
                        })
                        # update status
                        if t["status"] == "NOT_CONTACTED":
                            t["status"] = "IN_PLAY"
                        save_json(TOUCHES_PATH, touches)
                        save_json(TARGETS_PATH, targets)
                        st.success("Logged. Next step scheduled.")
                else:
                    st.info("Next step is a LinkedIn touch. Log it when complete.")
                    if st.button("Mark LinkedIn touch done", key=f"li_{t['id']}"):
                        touches.append({
                            "target_id": t["id"],
                            "action": na["action"],
                            "date": datetime.now().isoformat(timespec="seconds")
                        })
                        save_json(TOUCHES_PATH, touches)
                        st.success("Logged.")
            else:
                st.write("Cadence complete.")

            st.markdown("---")
            st.markdown("### Timeline")
            t_touches = [x for x in touches if x["target_id"] == t["id"]]
            if not t_touches:
                st.write("No touches yet.")
            else:
                for x in sorted(t_touches, key=lambda r: r["date"], reverse=True):
                    st.write(f"{x['date']} — {x['action']}")

# ---- Templates ----
with tabs[2]:
    st.subheader("Templates")
    st.write("Edit templates anytime. Variables: {{FirstName}}, {{Company}}, {{YourName}}")

    action_codes = [code for _,_,code in CADENCE if code.startswith("EMAIL")] + ["RECYCLE_Q4"]
    selected = st.selectbox("Template", action_codes)
    tpl = templates.get(selected, {"subject":"","body":""})

    subj = st.text_input("Subject", tpl.get("subject",""))
    body = st.text_area("Body", tpl.get("body",""), height=280)

    col1, col2 = st.columns(2)
    if col1.button("Save template"):
        templates[selected] = {"subject": subj, "body": body}
        save_json(TEMPLATES_PATH, templates)
        st.success("Saved.")
    if col2.button("Reset all to default"):
        templates = DEFAULT_TEMPLATES
        save_json(TEMPLATES_PATH, templates)
        st.success("Reset.")

# ---- Export ----
with tabs[3]:
    st.subheader("Export")
    st.write("Export for HubSpot import or backup.")

    df_targets = pd.DataFrame(targets)
    df_touches = pd.DataFrame(touches)

    st.download_button("Download Targets CSV", df_targets.to_csv(index=False).encode("utf-8"), "targets_export.csv", "text/csv")
    st.download_button("Download Touches CSV", df_touches.to_csv(index=False).encode("utf-8"), "touches_export.csv", "text/csv")

    st.divider()
    st.subheader("HubSpot Tasks Export (optional)")
    st.caption("Creates dated tasks for the NEXT action per target.")
    tasks = []
    for t in targets:
        na = next_action(t, touches, start_date)
        if not na: 
            continue
        tasks.append({
            "Task Name": f"{na['action']} — {t['company']}",
            "Due Date": na["due"].isoformat(),
            "Task Notes": f"Company: {t['company']}\nDomain: {t['domain']}\nContact: {t.get('contact_name','')}\nEmail: {t.get('email','')}\nNext: {na['label']}",
            "Company Name": t["company"],
            "Company Domain": t["domain"]
        })
    df_tasks = pd.DataFrame(tasks)
    st.download_button("Download HubSpot Tasks CSV", df_tasks.to_csv(index=False).encode("utf-8"), "hubspot_tasks_next_actions.csv", "text/csv")
