"""
core/generator.py — Anthropic API integration.

Generates tailored cover letters and resume bullet swaps for each approved job.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-sonnet-4-6"

CANDIDATE_PROFILE = """
Name:        Brandon Golas
Email:       brandx293@gmail.com
Phone:       908-209-6278
Location:    Sayreville, NJ
Work Auth:   US Citizen, no sponsorship needed
Salary:      $100,000 target (min $80,000)

Recent Experience:
- Director of Operations @ Garden State Air Conditioning & Heating (Dec 2025–Mar 2026)
  Built full operational infrastructure from scratch in 90 days — 18+ departments, CRM
  backend (HouseCall Pro + QuickBooks), AR/AP, vendor ecosystem (20+ partners), KPI
  dashboards, multi-channel marketing engine (7+ lead sources), sales department structure,
  inventory system, Zapier automations. Enabled $800K+ in funded revenue.

- Operations Manager @ Sam's Air Control (May 2024–Oct 2025)
  Hired/scaled team of 7–15 across HVAC, office, sales, project mgmt. Managed AR +
  financing programs enabling $800K+ funded revenue. Generated $200K+ via marketing
  funnels. Recovered $80K+ via equipment return process. Created KPI dashboards.

- Business Operations Intern @ GGD Grupa Gold Door, Poland (May–Sep 2022)
  Managed $40K international procurement, optimized container logistics.

Education: B.S. Chemistry, Rutgers University, May 2024. Bilingual: English + Polish.

Top 3 Proof Points:
1. Built 18+ departments from zero in 90 days
2. $800K+ in funded AR/revenue managed + $200K+ marketing revenue generated
3. Built CRM, KPI, inventory, and automation infrastructure twice from scratch
"""

BULLET_BANK = """
OPERATIONS INFRASTRUCTURE:
- Built full operational infrastructure from scratch at two companies (0→full ops in 90 days at latest role)
- Architected CRM backend (HouseCall Pro + QuickBooks) mapping job types/tagging to financial reporting
- Designed Zapier automations to close revenue-recognition gaps, eliminating reporting discrepancies
- Created organizational filing system across 18+ departments for scalable cross-functional alignment
- Built QR-code inventory replenishment system with real-time tracking, zero technician training needed

REVENUE & FINANCIAL OPS:
- Managed AR and customer financing programs (GoodLeap, Synchrony, OBR Utility) → $800K+ funded revenue
- Generated $200K+ in revenue through custom marketing funnels with end-to-end ownership
- Recovered $80K+ in one month through equipment return procedure + warehouse process redesign
- Negotiated vendor pricing, secured rebates, managed supplier partnerships to reduce material costs
- Stood up full financial ops function (AR, AP, financing, vendor pricing) at company with no prior structure

TEAM LEADERSHIP & SCALING:
- Hired and onboarded 7–15 staff across technical, office, sales, and PM functions from scratch
- Created new operational roles to support rapid growth and improve job throughput
- Built sales department end-to-end: commission models, quoting workflows, KPI dashboards, rep enablement
- Ran structured weekly ops meetings covering marketing, pipeline, CRM health, cross-dept priorities
- Managed 20+ vendor and platform relationships simultaneously

MARKETING & LEAD GENERATION:
- Launched multi-channel marketing engine with 7+ lead sources, driving steady residential/commercial pipeline
- Generated $200K+ in revenue through custom marketing funnels with full vendor and performance ownership
- Built KPI dashboards improving CSR booking rates via team role optimization and call routing

KPI, DATA & PROCESS:
- Built Zapier data collection workflows creating reliable KPI/job costing/accounting data layer
- Developed KPI dashboards tied directly to P&L outcomes across sales, ops, and CS functions
- Designed process automations eliminating manual reporting gaps across CRM, accounting, and inventory
"""


def call_anthropic(system_prompt: str, user_prompt: str, max_tokens: int = 1000) -> str:
    """Make a single call to the Anthropic API and return text."""
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set")
        return "[API key not configured]"
    headers = {
        "Content-Type":  "application/json",
        "x-api-key":     ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model":      MODEL,
        "max_tokens": max_tokens,
        "system":     system_prompt,
        "messages":   [{"role": "user", "content": user_prompt}],
    }
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=payload, timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        return f"[Generation failed: {e}]"


def generate_cover_letter(job: dict) -> str:
    system = f"""You are a professional cover letter writer working for Brandon Golas.
Write warm, direct, peer-level cover letters — confident but not arrogant, specific not generic.
3 paragraphs max, under 300 words. Never use "I am writing to express my interest" or similar
boilerplate openers. Always end with a low-pressure CTA for a call.
Return plain text only, no markdown, no subject line — just the letter body.

CANDIDATE PROFILE:
{CANDIDATE_PROFILE}
"""
    user = f"""Write a tailored cover letter for this job. Reference something specific about
the company or role — not generic.

JOB TITLE:   {job.get('title', '')}
COMPANY:     {job.get('company', '')}
LOCATION:    {job.get('location', '')}
SALARY:      {job.get('salary', 'Not Listed')}
LEVEL:       {job.get('level', '')}
INDUSTRY:    {job.get('industry', '')}
"""
    return call_anthropic(system, user, max_tokens=600)


def generate_bullets(job: dict) -> str:
    system = f"""You are a resume writer specializing in operations leadership.
Select and lightly adapt the 4-6 bullets from the provided bullet bank that most directly
mirror the language and requirements of the job description. Return a numbered list only.
Add a short [Category] label to each. Do not invent new bullets.

BULLET BANK:
{BULLET_BANK}
"""
    user = f"""Select the best 4-6 bullets for this role:

JOB TITLE:   {job.get('title', '')}
COMPANY:     {job.get('company', '')}
LEVEL:       {job.get('level', '')}
INDUSTRY:    {job.get('industry', '')}
"""
    return call_anthropic(system, user, max_tokens=600)


def generate_application_packet(job: dict) -> dict:
    """
    Generate both cover letter and tailored bullets.
    Returns dict with 'cover_letter', 'bullets', 'prefill' keys.
    """
    logger.info(f"Generating packet for {job.get('title')} @ {job.get('company')}")
    cover_letter = generate_cover_letter(job)
    bullets      = generate_bullets(job)
    prefill = {
        "Full Name":     "Brandon Golas",
        "Email":         "brandx293@gmail.com",
        "Phone":         "908-209-6278",
        "Address":       "Sayreville, NJ 08872",
        "Work Auth":     "US Citizen — no sponsorship needed",
        "Salary":        "100000",
        "Availability":  "2 weeks / immediate for right role",
        "Veteran":       "Not a veteran",
        "Disability":    "No disability",
        "Relocate":      "No",
        "Remote Pref":   "Open to hybrid or on-site",
    }
    return {
        "cover_letter": cover_letter,
        "bullets":      bullets,
        "prefill":      prefill,
    }
