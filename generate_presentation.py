"""
Generate B2_Grp_18_VLCDS_Updated.pptx and export to PDF.
Full 19-slide comprehensive presentation with all content, diagrams, benchmarks, and hardware results.
"""

import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# --- PATHS ---
PROJECT_DIR = r"d:\PROJECTS\CRY"
DIAGRAMS_DIR = os.path.join(PROJECT_DIR, "diagrams")
OUTPUT_PPTX = os.path.join(PROJECT_DIR, "B2_Grp_18_VLCDS_Updated.pptx")
OUTPUT_PDF = os.path.join(PROJECT_DIR, "B2_Grp_18_VLCDS_Updated.pdf")

# --- COLOR PALETTE ---
BG_DARK = RGBColor(0x0A, 0x11, 0x24)       # Very dark navy
BG_CARD = RGBColor(0x13, 0x22, 0x38)       # Slate card background
BG_CARD_BORDER = RGBColor(0x1E, 0x3A, 0x5F)# Border highlight
CYAN = RGBColor(0x00, 0xD4, 0xFF)          # Primary accent
GREEN = RGBColor(0x00, 0xE6, 0x76)         # Success / pass
RED = RGBColor(0xFF, 0x52, 0x52)           # Danger / attack
AMBER = RGBColor(0xFF, 0xD7, 0x40)         # Warning / note
PURPLE = RGBColor(0xB3, 0x88, 0xFF)        # Secondary accent
CORAL = RGBColor(0xFF, 0x6B, 0x35)         # Warm accent
WHITE = RGBColor(0xFF, 0xFF, 0xFF)         # Primary text
TEXT_LIGHT = RGBColor(0xCB, 0xD5, 0xE1)    # Body text
TEXT_MUTED = RGBColor(0x88, 0x99, 0xAA)    # Muted captions

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

def set_slide_bg(slide, color=BG_DARK):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_header(slide, tag, title, subtitle=None):
    # Tag
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = tag.upper()
    p.font.name = "Arial"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = CYAN
    
    # Title
    tb_t = slide.shapes.add_textbox(Inches(0.8), Inches(0.72), Inches(11.7), Inches(0.65))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title
    p_t.font.name = "Arial"
    p_t.font.size = Pt(26)
    p_t.font.bold = True
    p_t.font.color.rgb = WHITE
    
    # Subtitle
    if subtitle:
        tb_s = slide.shapes.add_textbox(Inches(0.8), Inches(1.35), Inches(11.7), Inches(0.45))
        tf_s = tb_s.text_frame
        tf_s.word_wrap = True
        p_s = tf_s.paragraphs[0]
        p_s.text = subtitle
        p_s.font.name = "Calibri"
        p_s.font.size = Pt(13)
        p_s.font.color.rgb = TEXT_MUTED

    # Footer
    tb_f = slide.shapes.add_textbox(Inches(0.8), Inches(7.0), Inches(11.7), Inches(0.3))
    tf_f = tb_f.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = "VLCDS: Version-Locked Chained Delta Signatures  |  B2_Grp_18  |  Cryptography Course Project"
    p_f.font.name = "Calibri"
    p_f.font.size = Pt(10)
    p_f.font.color.rgb = TEXT_MUTED

def add_card(slide, left, top, width, height, bg_color=BG_CARD, border_color=BG_CARD_BORDER):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    return shape

# ==============================================================================
# SLIDE 1: TITLE SLIDE
# ==============================================================================
slide1 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide1, BG_DARK)

# Decorative card background
add_card(slide1, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9), bg_color=RGBColor(0x0E, 0x1A, 0x30), border_color=CYAN)

# Category pill / banner
tb = slide1.shapes.add_textbox(Inches(1.2), Inches(1.2), Inches(10), Inches(0.4))
tf = tb.text_frame
p = tf.paragraphs[0]
p.text = "CRYPTOGRAPHY COURSE PROJECT  |  FINAL PROJECT PRESENTATION"
p.font.name = "Arial"
p.font.size = Pt(12)
p.font.bold = True
p.font.color.rgb = CYAN

# Main Title
tb = slide1.shapes.add_textbox(Inches(1.2), Inches(1.65), Inches(11), Inches(1.2))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Version-Locked Chained Delta Signatures (VLCDS)"
p.font.name = "Arial"
p.font.size = Pt(34)
p.font.bold = True
p.font.color.rgb = WHITE

# Subtitle
tb = slide1.shapes.add_textbox(Inches(1.2), Inches(2.85), Inches(10.8), Inches(0.8))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Extending Pre-Verify / Post-Verify Firmware Authentication to Secure Delta Updates on Resource-Constrained IoT Devices"
p.font.name = "Calibri"
p.font.size = Pt(17)
p.font.color.rgb = TEXT_LIGHT

# Base Paper & Reference
tb = slide1.shapes.add_textbox(Inches(1.2), Inches(3.75), Inches(10.8), Inches(0.8))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Base Paper: Formanek et al., 'Advanced System for Remote Updates on ESP32-Based Devices Using OTA Update Technology,' Computers (MDPI), Vol. 14, Issue 12, Art. 531, 2025."
p.font.name = "Calibri"
p.font.size = Pt(11.5)
p.font.color.rgb = TEXT_MUTED
p2 = tf.add_paragraph()
p2.text = "Prior Technique Adapted: US10206114B2 / US10887770B2 (Samsung) — Pre-Verify / Post-Verify Dual Firmware Verification"
p2.font.name = "Calibri"
p2.font.size = Pt(11.5)
p2.font.color.rgb = TEXT_MUTED

# Authors & Details Box
add_card(slide1, Inches(1.2), Inches(4.75), Inches(10.9), Inches(1.5), bg_color=RGBColor(0x16, 0x2A, 0x48), border_color=None)

tb = slide1.shapes.add_textbox(Inches(1.5), Inches(4.85), Inches(10.3), Inches(1.3))
tf = tb.text_frame
p = tf.paragraphs[0]
p.text = "Project Team: B2_Grp_18"
p.font.name = "Arial"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = CYAN

p_auth = tf.add_paragraph()
p_auth.text = "Vatsal Shrivastava   |   Nisarg Shilpesh Nagar   |   Johns Maria Joy"
p_auth.font.name = "Arial"
p_auth.font.size = Pt(16)
p_auth.font.bold = True
p_auth.font.color.rgb = WHITE
p_auth.space_before = Pt(4)

p_guide = tf.add_paragraph()
p_guide.text = "Course Instructor & Evaluator: Karthika V  •  Implementation: PC Simulator + ESP32-S2 Hardware"
p_guide.font.name = "Calibri"
p_guide.font.size = Pt(12)
p_guide.font.color.rgb = TEXT_LIGHT
p_guide.space_before = Pt(4)


# ==============================================================================
# SLIDE 2: INTRODUCTION — WHAT THE BASE PAPER DELIVERS
# ==============================================================================
slide2 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide2)
add_header(slide2, "1. Introduction", "What the Base Paper Delivers", "Formanek et al. (Computers MDPI, 2025) — State-of-the-Art Remote OTA for ESP32 Devices")

features = [
    ("01", "Centralized Release Routing", "Server-driven mechanism dynamically routes correct firmware versions to targeted device classes across heterogeneous deployments.", CYAN),
    ("02", "Multi-Protocol Delivery", "Supports diverse IoT transport layers including HTTP, MQTT, and CoAP to reach constrained and distributed wireless endpoints.", PURPLE),
    ("03", "Version Checks & Rollback", "Safety fallback mechanism automatically restores previous operational firmware if update fails boot or verification.", AMBER),
    ("04", "Delta (Differential) Updates", "Transmits only binary diffs between installed and target firmware, drastically cutting wireless transmission bandwidth and flash wear.", GREEN)
]

for i, (num, title, desc, clr) in enumerate(features):
    x = Inches(0.8 + (i % 2) * 5.95)
    y = Inches(1.9 + (i // 2) * 2.1)
    add_card(slide2, x, y, Inches(5.75), Inches(1.9), border_color=clr)
    
    tb = slide2.shapes.add_textbox(x + Inches(0.25), y + Inches(0.2), Inches(5.25), Inches(1.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = f"{num}  •  {title}"
    p.font.name = "Arial"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = clr
    
    p2 = tf.add_paragraph()
    p2.text = desc
    p2.font.name = "Calibri"
    p2.font.size = Pt(13)
    p2.font.color.rgb = TEXT_LIGHT
    p2.space_before = Pt(8)

# Baseline callout bar
add_card(slide2, Inches(0.8), Inches(6.15), Inches(11.7), Inches(0.7), bg_color=RGBColor(0x10, 0x25, 0x40), border_color=CYAN)
tb = slide2.shapes.add_textbox(Inches(1.0), Inches(6.2), Inches(11.3), Inches(0.6))
tf = tb.text_frame
p = tf.paragraphs[0]
p.text = "Reported ESP32 Cryptographic Baseline in Base Paper:  ~4.8 ms / 3.5 mJ (Ed25519 verify)  •  ~25 ms / 2.4 mJ (SHA-256 over 1 MB)"
p.font.name = "Arial"
p.font.size = Pt(12)
p.font.bold = True
p.font.color.rgb = WHITE


# ==============================================================================
# SLIDE 3: PROBLEM STATEMENT
# ==============================================================================
slide3 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide3)
add_header(slide3, "2. Problem Statement", "Content Is Authenticated — Version & History Are Not", "The Critical Vulnerability in Modern IoT Firmware Update Pipelines")

# Context card
add_card(slide3, Inches(0.8), Inches(1.9), Inches(11.7), Inches(1.2), border_color=CYAN)
tb = slide3.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(1.0))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Resource-constrained IoT devices (ESP32-class) increasingly rely on delta firmware updates over lossy, low-bandwidth wireless links (BLE, LoRa, cellular). Existing signature verification either executes only after the full image is assembled in flash, or verifies binary image integrity alone — NEVER cryptographically binding the patch to the installed version or historical update chain."
p.font.name = "Calibri"
p.font.size = Pt(13.5)
p.font.color.rgb = WHITE

# Two Major Failure Modes
cards_data = [
    ("FAIL-01: Wasted Flash, Energy & Bandwidth",
     "A mismatched-base or replayed patch is downloaded and partially processed before failure is discovered at post-verify.\n"
     "• Constrained nodes burn up to 90% of wireless battery budget downloading non-applicable deltas.\n"
     "• Unnecessary flash erase/write cycles permanently degrade MCU flash memory endurance.",
     CORAL),
    ("FAIL-02: Bypassable State & Rollback Protection",
     "Traditional systems store version numbers in unauthenticated plaintext headers or external JSON metadata.\n"
     "• An attacker can alter version metadata without invalidating content signatures.\n"
     "• Replaying an old, signed firmware image (forced rollback attack) reinstalls known vulnerabilities.",
     RED)
]

for i, (title, desc, clr) in enumerate(cards_data):
    x = Inches(0.8 + i * 5.95)
    add_card(slide3, x, Inches(3.25), Inches(5.75), Inches(2.4), border_color=clr)
    tb = slide3.shapes.add_textbox(x + Inches(0.25), Inches(3.35), Inches(5.25), Inches(2.2))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = "Arial"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = clr
    
    p2 = tf.add_paragraph()
    p2.text = desc
    p2.font.name = "Calibri"
    p2.font.size = Pt(12.5)
    p2.font.color.rgb = TEXT_LIGHT
    p2.space_before = Pt(8)

# Research Question
add_card(slide3, Inches(0.8), Inches(5.8), Inches(11.7), Inches(1.05), bg_color=RGBColor(0x10, 0x2A, 0x48), border_color=AMBER)
tb = slide3.shapes.add_textbox(Inches(1.0), Inches(5.85), Inches(11.3), Inches(0.95))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "RESEARCH QUESTION: How can a delta firmware update be cryptographically bound — BEFORE any patch bytes are transferred or applied — to the exact base version, target version, and historical chain head, using minimal overhead suitable for low-power IoT microcontrollers?"
p.font.name = "Arial"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = AMBER


# ==============================================================================
# SLIDE 4: RESEARCH GAP
# ==============================================================================
slide4 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide4)
add_header(slide4, "3. Research Gap", "Two Independent Lines of Prior Work", "Analyzing Why Neither Approach Solves the Secure Delta Problem")

# Left Column: Base Paper
add_card(slide4, Inches(0.8), Inches(1.9), Inches(5.75), Inches(3.5), border_color=CYAN)
tb = slide4.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.35), Inches(3.2))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Line 1: Base Paper's Delta Pipeline"
p.font.name = "Arial"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = CYAN

p_sub = tf.add_paragraph()
p_sub.text = "Formanek et al., Computers (MDPI), 2025"
p_sub.font.name = "Calibri"
p_sub.font.size = Pt(12)
p_sub.font.color.rgb = TEXT_MUTED

points_1 = [
    "Optimizes bandwidth, power, and transmission time for delta updates on ESP32.",
    "Cryptographic authentication and tamper-resistance explicitly left as future work.",
    "Version checking and rollback handling rely solely on unauthenticated application logic.",
    "Vulnerable to malicious patch injection, version spoofing, and MITM tampering."
]
for pt in points_1:
    p_pt = tf.add_paragraph()
    p_pt.text = "•  " + pt
    p_pt.font.name = "Calibri"
    p_pt.font.size = Pt(12)
    p_pt.font.color.rgb = TEXT_LIGHT
    p_pt.space_before = Pt(6)

# Right Column: Samsung Patent
add_card(slide4, Inches(6.75), Inches(1.9), Inches(5.75), Inches(3.5), border_color=PURPLE)
tb = slide4.shapes.add_textbox(Inches(6.95), Inches(2.05), Inches(5.35), Inches(3.2))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "Line 2: Samsung Pre-/Post-Verify Patents"
p.font.name = "Arial"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = PURPLE

p_sub = tf.add_paragraph()
p_sub.text = "US10206114B2 / US10887770B2 (Samsung Electronics)"
p_sub.font.name = "Calibri"
p_sub.font.size = Pt(12)
p_sub.font.color.rgb = TEXT_MUTED

points_2 = [
    "Patented for smartphone / NFC secure elements communicating over an on-board bus (I2C/SPI).",
    "Only evaluates full monolithic firmware images — delta patches are not addressed.",
    "Version numbers and replay tracking are external to the cryptographically signed object.",
    "Assumes reliable local wiring, not lossy wireless links with malicious network adversaries."
]
for pt in points_2:
    p_pt = tf.add_paragraph()
    p_pt.text = "•  " + pt
    p_pt.font.name = "Calibri"
    p_pt.font.size = Pt(12)
    p_pt.font.color.rgb = TEXT_LIGHT
    p_pt.space_before = Pt(6)

# Consolidated Gap Box
add_card(slide4, Inches(0.8), Inches(5.55), Inches(11.7), Inches(1.3), bg_color=RGBColor(0x1B, 0x20, 0x38), border_color=CORAL)
tb = slide4.shapes.add_textbox(Inches(1.0), Inches(5.65), Inches(11.3), Inches(1.15))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "CONSOLIDATED RESEARCH GAP:"
p.font.name = "Arial"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = CORAL

p_gap = tf.add_paragraph()
p_gap.text = "No existing protocol cryptographically binds delta patch content, device installed state, target version, and historical chain head into a single pre-verification object. Constrained wireless IoT endpoints have lacked a zero-waste gatekeeper that aborts invalid updates before receiving payload bytes."
p_gap.font.name = "Calibri"
p_gap.font.size = Pt(13)
p_gap.font.color.rgb = WHITE
p_gap.space_before = Pt(4)


# ==============================================================================
# SLIDE 5: METHODOLOGY — SIX-PHASE RESEARCH APPROACH (WITH DIAGRAM)
# ==============================================================================
slide5 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide5)
add_header(slide5, "4. Research Methodology", "Six-Phase Engineering & Validation Methodology", "Rigorous Engineering Workflow from Formal Modeling to Physical Hardware Validation")

# Diagram on Left
diag_path = os.path.join(DIAGRAMS_DIR, "methodology_diagram.jpg")
if os.path.exists(diag_path):
    add_card(slide5, Inches(0.8), Inches(1.8), Inches(5.2), Inches(4.9), bg_color=RGBColor(0x0C, 0x16, 0x2A), border_color=CYAN)
    slide5.shapes.add_picture(diag_path, Inches(0.9), Inches(1.9), Inches(5.0), Inches(4.7))

# Phase breakdown on Right
add_card(slide5, Inches(6.2), Inches(1.8), Inches(6.3), Inches(4.9), border_color=BG_CARD_BORDER)
tb = slide5.shapes.add_textbox(Inches(6.4), Inches(1.9), Inches(5.9), Inches(4.7))
tf = tb.text_frame
tf.word_wrap = True

phases = [
    ("Phase 1: Problem Analysis", "Identified IoT OTA vulnerabilities: bandwidth waste, flash burnout, rollback exploits.", CYAN),
    ("Phase 2: Threat Modeling", "Adopted Dolev-Yao network attacker model; selected Ed25519 (RFC 8032) & SHA-256.", PURPLE),
    ("Phase 3: Protocol Architecture", "Designed 6-field manifest, 3-stage verification flow, and cryptographic hash-chain.", GREEN),
    ("Phase 4: Dual Implementation", "Full PC reference simulation in Python 3.12 + physical ESP32-S2 MicroPython drivers.", AMBER),
    ("Phase 5: Empirical Benchmarking", "Comprehensive 13-test PyTest suite, 100-run crypto benchmarks, automated attack suite.", CORAL),
    ("Phase 6: Live Validation", "Hardware deployment on ESP32-S2 DevKit M1 over WiFi HTTP with real-time web dashboard.", WHITE)
]

for i, (title, desc, clr) in enumerate(phases):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.text = f"{i+1}. {title}"
    p.font.name = "Arial"
    p.font.size = Pt(13.5)
    p.font.bold = True
    p.font.color.rgb = clr
    if i > 0:
        p.space_before = Pt(8)
    
    p_desc = tf.add_paragraph()
    p_desc.text = desc
    p_desc.font.name = "Calibri"
    p_desc.font.size = Pt(11.5)
    p_desc.font.color.rgb = TEXT_LIGHT
    p_desc.space_before = Pt(2)


# ==============================================================================
# SLIDE 6: PROPOSED CONTRIBUTION — THE VLCDS PROTOCOL
# ==============================================================================
slide6 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide6)
add_header(slide6, "5. Proposed Contribution", "The VLCDS Protocol Architecture", "One 200-Byte Signed Manifest Binds Six Critical Facts Together")

# Formula Box
add_card(slide6, Inches(0.8), Inches(1.85), Inches(11.7), Inches(1.2), bg_color=RGBColor(0x10, 0x22, 0x40), border_color=CYAN)
tb = slide6.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(11.3), Inches(1.0))
tf = tb.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
p.text = "CRYPTOGRAPHIC MANIFEST EQUATION:"
p.font.name = "Arial"
p.font.size = Pt(12)
p.font.bold = True
p.font.color.rgb = CYAN

p_eq = tf.add_paragraph()
p_eq.text = "M = Sign_privkey( H(base_fw) || H(delta) || H(target) || ver_base || ver_target || H(prev_manifest) )"
p_eq.font.name = "Consolas"
p_eq.font.size = Pt(16)
p_eq.font.bold = True
p_eq.font.color.rgb = WHITE
p_eq.space_before = Pt(4)

# Three Dimensions of Binding
binding_types = [
    ("CONTENT BINDING", "3 × 32-Byte SHA-256 Hashes",
     "• H(base_fw): Cryptographically verifies current running image.\n"
     "• H(delta): Authenticates incoming patch before transfer.\n"
     "• H(target): Locks expected final state into signature.",
     CYAN),
    ("STATE BINDING", "2 × 4-Byte Integer Versions",
     "• ver_base: Expected active firmware version.\n"
     "• ver_target: Target version after patch.\n"
     "• Prevents version manipulation and cross-version patching.",
     AMBER),
    ("HISTORY BINDING", "1 × 32-Byte Hash-Chain Head",
     "• H(prev_manifest): SHA-256 of last accepted manifest.\n"
     "• Forms an unalterable blockchain-style history.\n"
     "• Completely neutralizes replay / rollback attacks.",
     GREEN)
]

for i, (b_title, b_sub, b_body, clr) in enumerate(binding_types):
    x = Inches(0.8 + i * 3.97)
    add_card(slide6, x, Inches(3.2), Inches(3.8), Inches(3.5), border_color=clr)
    tb = slide6.shapes.add_textbox(x + Inches(0.2), Inches(3.3), Inches(3.4), Inches(3.3))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = b_title
    p.font.name = "Arial"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = clr
    
    p_sub = tf.add_paragraph()
    p_sub.text = b_sub
    p_sub.font.name = "Arial"
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = TEXT_MUTED
    p_sub.space_before = Pt(2)
    
    p_body = tf.add_paragraph()
    p_body.text = b_body
    p_body.font.name = "Calibri"
    p_body.font.size = Pt(12)
    p_body.font.color.rgb = TEXT_LIGHT
    p_body.space_before = Pt(10)


# ==============================================================================
# SLIDE 7: SYSTEM ARCHITECTURE (WITH DIAGRAM)
# ==============================================================================
slide7 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide7)
add_header(slide7, "6. System Architecture", "End-to-End VLCDS Deployment Topology", "OTA Vendor Server (PC) Interacting with IoT Edge Device (ESP32-S2) Over Untrusted Wireless")

diag_path = os.path.join(DIAGRAMS_DIR, "system_architecture_1790185624236.jpg")
if os.path.exists(diag_path):
    add_card(slide7, Inches(0.8), Inches(1.8), Inches(11.733), Inches(4.9), bg_color=RGBColor(0x0C, 0x16, 0x2A), border_color=CYAN)
    slide7.shapes.add_picture(diag_path, Inches(0.9), Inches(1.9), Inches(11.533), Inches(4.7))


# ==============================================================================
# SLIDE 8: MANIFEST STRUCTURE DEEP-DIVE (WITH DIAGRAM)
# ==============================================================================
slide8 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide8)
add_header(slide8, "7. Manifest Structure", "200-Byte Binary Wire Format Layout", "Extremely Compact Wire Representation Tailored for Constrained Wireless MTUs")

# Diagram on Left
diag_path = os.path.join(DIAGRAMS_DIR, "manifest_structure_1790185678069.jpg")
if os.path.exists(diag_path):
    add_card(slide8, Inches(0.8), Inches(1.8), Inches(6.0), Inches(4.9), bg_color=RGBColor(0x0C, 0x16, 0x2A), border_color=CYAN)
    slide8.shapes.add_picture(diag_path, Inches(0.9), Inches(1.9), Inches(5.8), Inches(4.7))

# Table & MTU specs on Right
add_card(slide8, Inches(7.0), Inches(1.8), Inches(5.5), Inches(4.9), border_color=BG_CARD_BORDER)
tb = slide8.shapes.add_textbox(Inches(7.2), Inches(1.9), Inches(5.1), Inches(4.7))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "FIELD SPECIFICATIONS (200 BYTES)"
p.font.name = "Arial"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = CYAN

fields = [
    ("H(base_fw)", "32 Bytes", "SHA-256 hash of active firmware"),
    ("H(delta)", "32 Bytes", "SHA-256 hash of delta patch"),
    ("H(target)", "32 Bytes", "SHA-256 hash of reconstructed image"),
    ("ver_base", "4 Bytes", "uint32 expected base version"),
    ("ver_target", "4 Bytes", "uint32 new target version"),
    ("H(prev_manifest)", "32 Bytes", "SHA-256 hash of previous manifest"),
    ("signature", "64 Bytes", "Ed25519 signature (RFC 8032)")
]

for name, size, desc in fields:
    p_f = tf.add_paragraph()
    p_f.text = f"• {name} ({size}): {desc}"
    p_f.font.name = "Calibri"
    p_f.font.size = Pt(11)
    p_f.font.color.rgb = TEXT_LIGHT
    p_f.space_before = Pt(3)

p_mtu = tf.add_paragraph()
p_mtu.text = "WIRELESS MTU COMPATIBILITY:"
p_mtu.font.name = "Arial"
p_mtu.font.size = Pt(12)
p_mtu.font.bold = True
p_mtu.font.color.rgb = GREEN
p_mtu.space_before = Pt(12)

mtu_points = [
    "LoRaWAN: Max payload 222 B -> Entire manifest fits in 1 frame!",
    "BLE (Bluetooth 5.0+): MTU up to 244 B -> Single packet transmission.",
    "Zigbee (802.15.4): Fits with lightweight 2-frame fragmentation.",
    "CoAP / UDP: Transmitted inside a single non-fragmented datagram."
]
for mp in mtu_points:
    p_m = tf.add_paragraph()
    p_m.text = "✓ " + mp
    p_m.font.name = "Calibri"
    p_m.font.size = Pt(10.5)
    p_m.font.color.rgb = WHITE
    p_m.space_before = Pt(2)


# ==============================================================================
# SLIDE 9: 3-STAGE VERIFICATION PIPELINE (WITH DIAGRAM)
# ==============================================================================
slide9 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide9)
add_header(slide9, "8. Verification Protocol", "The 3-Stage Zero-Waste Verification Pipeline", "How VLCDS Eliminates Wasted Bandwidth and Avoids Redundant Signatures")

# Diagram on Left
diag_path = os.path.join(DIAGRAMS_DIR, "verification_flowchart_1790185640405.jpg")
if os.path.exists(diag_path):
    add_card(slide9, Inches(0.8), Inches(1.8), Inches(5.4), Inches(4.9), bg_color=RGBColor(0x0C, 0x16, 0x2A), border_color=CYAN)
    slide9.shapes.add_picture(diag_path, Inches(0.9), Inches(1.9), Inches(5.2), Inches(4.7))

# Descriptions on Right
add_card(slide9, Inches(6.4), Inches(1.8), Inches(6.1), Inches(4.9), border_color=BG_CARD_BORDER)
tb = slide9.shapes.add_textbox(Inches(6.6), Inches(1.9), Inches(5.7), Inches(4.7))
tf = tb.text_frame
tf.word_wrap = True

stage_info = [
    ("STAGE 1: PRE-VERIFICATION (Gatekeeper)",
     "Executed BEFORE requesting or downloading any patch bytes:\n"
     "1. Verify Ed25519 signature over 6-field manifest.\n"
     "2. Confirm H(base_fw) matches device's current SHA-256.\n"
     "3. Confirm ver_base matches currently running version.\n"
     "4. Confirm H(prev_manifest) matches device's chain head.\n"
     "--> IF ANY CHECK FAILS: Abort instantly. ZERO patch bytes wasted!",
     CORAL),
    ("STAGE 2: TRANSFER & APPLY",
     "Triggered only after Stage 1 passes:\n"
     "1. Device requests delta patch payload from server.\n"
     "2. Verifies SHA-256 of received delta equals authenticated H(delta).\n"
     "3. Applies differential patch to shadow partition in flash.",
     CYAN),
    ("STAGE 3: POST-VERIFICATION (Zero Signature Overhead)",
     "Final safety confirmation:\n"
     "1. Compute SHA-256 of reconstructed firmware on shadow partition.\n"
     "2. Compare against H(target) committed inside Stage-1 signature.\n"
     "3. Flip active boot partition -> Reboot to new version!\n"
     "--> NO EXPENSIVE 2ND SIGNATURE CHECK NEEDED!",
     GREEN)
]

for i, (title, body, clr) in enumerate(stage_info):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.text = title
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = clr
    if i > 0:
        p.space_before = Pt(8)
    
    p_b = tf.add_paragraph()
    p_b.text = body
    p_b.font.name = "Calibri"
    p_b.font.size = Pt(11)
    p_b.font.color.rgb = TEXT_LIGHT
    p_b.space_before = Pt(2)


# ==============================================================================
# SLIDE 10: ANTI-REPLAY MECHANISM — HASH-CHAIN (WITH DIAGRAM)
# ==============================================================================
slide10 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide10)
add_header(slide10, "9. Anti-Replay Mechanism", "Cryptographic Manifest Hash-Chaining", "Preventing Forced Rollbacks and Stale Update Replays Without External State")

diag_path = os.path.join(DIAGRAMS_DIR, "hash_chain_1790185706802.jpg")
if os.path.exists(diag_path):
    add_card(slide10, Inches(0.8), Inches(1.8), Inches(11.733), Inches(4.9), bg_color=RGBColor(0x0C, 0x16, 0x2A), border_color=GREEN)
    slide10.shapes.add_picture(diag_path, Inches(0.9), Inches(1.9), Inches(11.533), Inches(4.7))


# ==============================================================================
# SLIDE 11: SECURITY ANALYSIS & ATTACK DEFENSE (WITH DIAGRAM)
# ==============================================================================
slide11 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide11)
add_header(slide11, "10. Security Analysis", "Attack Scenarios & Defense Validation", "Dolev-Yao Network Adversary: 100% Detection Rate Across All Simulated Attack Vectors")

diag_path = os.path.join(DIAGRAMS_DIR, "attack_defense_1790185692390.jpg")
if os.path.exists(diag_path):
    add_card(slide11, Inches(0.8), Inches(1.8), Inches(11.733), Inches(4.9), bg_color=RGBColor(0x0C, 0x16, 0x2A), border_color=RED)
    slide11.shapes.add_picture(diag_path, Inches(0.9), Inches(1.9), Inches(11.533), Inches(4.7))


# ==============================================================================
# SLIDE 12: DUAL IMPLEMENTATION ARCHITECTURE
# ==============================================================================
slide12 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide12)
add_header(slide12, "11. Implementation", "Dual Implementation Architecture", "Reference Python Simulation + Native ESP32-S2 MicroPython Drivers")

# Left: PC Simulation
add_card(slide12, Inches(0.8), Inches(1.9), Inches(5.75), Inches(4.8), border_color=CYAN)
tb = slide12.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.35), Inches(4.5))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "PC SIMULATION (Python 3.12)"
p.font.name = "Arial"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = CYAN

pc_components = [
    ("vlcds/crypto_utils.py", "Ed25519 (PyNaCl) + SHA-256 (hashlib) cryptographic primitives."),
    ("vlcds/manifest.py", "200-byte binary serializer, deserializer, and verification engine."),
    ("vlcds/delta_engine.py", "Binary XOR differential patching engine for IoT firmware."),
    ("vlcds/device.py", "Simulated IoT node with dual flash partitions and 3-stage pipeline."),
    ("vlcds/server.py", "OTA vendor update server managing repository and delta generation."),
    ("vlcds/chain.py", "Manifest hash-chain validator enforcing forward-only update order."),
    ("server_http.py", "Flask HTTP REST server serving real-world OTA requests to ESP32."),
    ("webapp.py", "Interactive browser dashboard demonstrating live attack simulations.")
]

for name, desc in pc_components:
    p_c = tf.add_paragraph()
    p_c.text = f"• {name}: {desc}"
    p_c.font.name = "Calibri"
    p_c.font.size = Pt(11.5)
    p_c.font.color.rgb = TEXT_LIGHT
    p_c.space_before = Pt(3)

# Right: ESP32 Hardware
add_card(slide12, Inches(6.75), Inches(1.9), Inches(5.75), Inches(4.8), border_color=GREEN)
tb = slide12.shapes.add_textbox(Inches(6.95), Inches(2.05), Inches(5.35), Inches(4.5))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "HARDWARE PLATFORM (ESP32-S2)"
p.font.name = "Arial"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = GREEN

hw_components = [
    ("ESP32-S2 DevKit M1", "Xtensa LX7 32CPU @ 240 MHz, 320 KB SRAM, 4 MB SPI Flash."),
    ("MicroPython v1.23.0", "Bare-metal runtime executing lightweight cryptographic client."),
    ("esp32/ed25519_mp.py", "Pure-Python Ed25519 digital signature implementation."),
    ("esp32/sha512_mp.py", "Pure-Python SHA-512 engine providing hash core for Ed25519."),
    ("esp32/vlcds_device.py", "Embedded VLCDS client implementing the full 3-stage verifier."),
    ("WiFi OTA Client", "Fetches signed manifest, runs pre-verify, then downloads delta."),
    ("Partition Management", "Dual slot emulation (Active vs Shadow slot) with integrity rollback."),
    ("Hardware Independence", "Zero dependency on proprietary C-blobs; 100% auditable Python.")
]

for name, desc in hw_components:
    p_h = tf.add_paragraph()
    p_h.text = f"• {name}: {desc}"
    p_h.font.name = "Calibri"
    p_h.font.size = Pt(11.5)
    p_h.font.color.rgb = TEXT_LIGHT
    p_h.space_before = Pt(3)


# ==============================================================================
# SLIDE 13: DELTA COMPRESSION & BANDWIDTH SAVINGS
# ==============================================================================
slide13 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide13)
add_header(slide13, "12. Bandwidth Optimization", "Delta Compression & Transmission Efficiency", "Quantifying Bandwidth Reductions and Flash Wear Savings")

# 3 Stat Cards
stat_cards = [
    ("FULL FIRMWARE IMAGE", "2,393 Bytes", "Monolithic binary transmission size required by conventional OTA.", TEXT_MUTED),
    ("VLCDS DELTA PATCH", "1,636 Bytes", "Differential XOR patch containing only modified firmware bytes.", CYAN),
    ("BANDWIDTH REDUCTION", "31.6% SAVED", "757 bytes cut per transmission; scales exponentially on larger MB images.", GREEN)
]

for i, (stitle, sval, sdesc, clr) in enumerate(stat_cards):
    x = Inches(0.8 + i * 3.97)
    add_card(slide13, x, Inches(1.9), Inches(3.8), Inches(1.8), border_color=clr)
    tb = slide13.shapes.add_textbox(x + Inches(0.2), Inches(2.0), Inches(3.4), Inches(1.6))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = stitle
    p.font.name = "Arial"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = clr
    
    p_v = tf.add_paragraph()
    p_v.text = sval
    p_v.font.name = "Arial"
    p_v.font.size = Pt(28)
    p_v.font.bold = True
    p_v.font.color.rgb = WHITE
    p_v.space_before = Pt(2)
    
    p_d = tf.add_paragraph()
    p_d.text = sdesc
    p_d.font.name = "Calibri"
    p_d.font.size = Pt(11)
    p_d.font.color.rgb = TEXT_LIGHT
    p_d.space_before = Pt(4)

# Bandwidth Analysis Box
add_card(slide13, Inches(0.8), Inches(3.9), Inches(11.7), Inches(2.8), border_color=AMBER)
tb = slide13.shapes.add_textbox(Inches(1.0), Inches(4.05), Inches(11.3), Inches(2.5))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "BANDWIDTH & ENERGY IMPLICATIONS UNDER ATTACK"
p.font.name = "Arial"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = AMBER

savings_details = [
    ("Conventional OTA Baseline", "Device downloads entire 2,393-byte image before checking signature -> Under attack: 2,393 bytes wasted, high radio energy burned, flash cycles consumed."),
    ("Naive Delta OTA", "Device downloads full 1,636-byte delta patch, applies it, fails at post-verify -> Under attack: 1,636 bytes wasted, shadow flash partition written and worn out."),
    ("VLCDS Protocol (Our Solution)", "Device exchanges ONLY the 200-byte manifest in Stage 1 -> Under attack: Aborts immediately, saving 1,636 bytes (100% of patch) and 0 flash writes!"),
    ("Net Payload Overhead", "Adding the 200-byte manifest to a valid 1,636-byte delta yields 1,836 bytes total -> Still 23.3% smaller than transferring the raw 2,393-byte firmware image!")
]

for title, desc in savings_details:
    p_s = tf.add_paragraph()
    p_s.text = f"• {title}: {desc}"
    p_s.font.name = "Calibri"
    p_s.font.size = Pt(12)
    p_s.font.color.rgb = TEXT_LIGHT
    p_s.space_before = Pt(5)


# ==============================================================================
# SLIDE 14: PERFORMANCE BENCHMARKS & PROFILING
# ==============================================================================
slide14 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide14)
add_header(slide14, "13. Performance Benchmarks", "Cryptographic Execution Profiling", "100-Iteration Microbenchmarks: Mean, Min, Max Timings (PC Python 3.12 Reference)")

# Crypto Benchmark Table
add_card(slide14, Inches(0.8), Inches(1.9), Inches(6.8), Inches(4.8), border_color=CYAN)
tb = slide14.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(6.4), Inches(4.6))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "MICROBENCHMARK TIMINGS (100 ITERATIONS)"
p.font.name = "Arial"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = CYAN

table_rows = [
    ("Ed25519 Sign (Manifest)", "0.1192 ms", "0.0991 ms", "0.1944 ms"),
    ("Ed25519 Verify (Manifest)", "0.3814 ms", "0.2792 ms", "0.4444 ms"),
    ("SHA-256 (1 KB payload)", "0.0061 ms", "0.0055 ms", "0.0297 ms"),
    ("SHA-256 (10 KB payload)", "0.0201 ms", "0.0196 ms", "0.0399 ms"),
    ("SHA-256 (100 KB payload)", "0.1539 ms", "0.1508 ms", "0.2900 ms"),
    ("SHA-256 (1,024 KB payload)", "1.5403 ms", "1.5173 ms", "1.7496 ms"),
]

for op, mean, mn, mx in table_rows:
    p_r = tf.add_paragraph()
    p_r.text = f"{op:<28} | Mean: {mean:<9} (Min: {mn}, Max: {mx})"
    p_r.font.name = "Consolas"
    p_r.font.size = Pt(11)
    p_r.font.color.rgb = TEXT_LIGHT
    p_r.space_before = Pt(4)

p_note = tf.add_paragraph()
p_note.text = "--> Digital signature verification dominates execution time; SHA-256 hashing cost is virtually negligible (<0.02 ms for IoT delta patches)."
p_note.font.name = "Calibri"
p_note.font.size = Pt(11)
p_note.font.color.rgb = TEXT_MUTED
p_note.space_before = Pt(8)

# Right: Overhead Comparison
add_card(slide14, Inches(7.8), Inches(1.9), Inches(4.7), Inches(4.8), border_color=AMBER)
tb = slide14.shapes.add_textbox(Inches(8.0), Inches(2.0), Inches(4.3), Inches(4.6))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "VLCDS VS BASELINE OVERHEAD"
p.font.name = "Arial"
p.font.size = Pt(13)
p.font.bold = True
p.font.color.rgb = AMBER

p_bl = tf.add_paragraph()
p_bl.text = "Single-Signature Baseline:\n1 Hash + 1 Sign + 1 Verify\n= 0.5066 ms"
p_bl.font.name = "Consolas"
p_bl.font.size = Pt(12)
p_bl.font.color.rgb = WHITE
p_bl.space_before = Pt(8)

p_vl = tf.add_paragraph()
p_vl.text = "VLCDS Proposed Protocol:\n5 Hashes + 1 Sign + 1 Verify\n= 0.5308 ms"
p_vl.font.name = "Consolas"
p_vl.font.size = Pt(12)
p_vl.font.color.rgb = GREEN
p_vl.space_before = Pt(10)

p_diff = tf.add_paragraph()
p_diff.text = "NET OVERHEAD:\n+0.0242 ms (+4.8%)\n"
p_diff.font.name = "Arial"
p_diff.font.size = Pt(18)
p_diff.font.bold = True
p_diff.font.color.rgb = CYAN
p_diff.space_before = Pt(10)

p_conc = tf.add_paragraph()
p_conc.text = "VLCDS provides Content + State + History authentication for less than 5% computational overhead compared to insecure single-signature schemes!"
p_conc.font.name = "Calibri"
p_conc.font.size = Pt(11.5)
p_conc.font.color.rgb = TEXT_LIGHT
p_conc.space_before = Pt(4)


# ==============================================================================
# SLIDE 15: HARDWARE VALIDATION (ESP32-S2 DEVKIT M1)
# ==============================================================================
slide15 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide15)
add_header(slide15, "14. Hardware Validation", "ESP32-S2 DevKit M1 Real Hardware Results", "Measured On-Chip Execution Performance of Native MicroPython Firmware")

# Left Column: Hardware Specifications & Timings
add_card(slide15, Inches(0.8), Inches(1.9), Inches(5.75), Inches(4.8), border_color=GREEN)
tb = slide15.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.35), Inches(4.5))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "MEASURED ESP32-S2 ON-CHIP TIMINGS"
p.font.name = "Arial"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = GREEN

hw_timings = [
    ("Ed25519 Signature Verify", "~237 ms", "Pure-Python math on 240 MHz Xtensa LX7"),
    ("SHA-256 Firmware Hash", "~12 ms", "Native hashlib engine on ESP32-S2"),
    ("Stage 1 (Pre-Verification)", "~253 ms", "All 4 cryptographic & state checks"),
    ("Stage 2 (Apply XOR Delta)", "~15 ms", "In-memory / flash shadow reconstruction"),
    ("Stage 3 (Post-Verification)", "~12 ms", "Hash equality check (Zero-signature!)"),
    ("Total Update Duration", "~280 ms", "Complete 3-stage validation cycle")
]

for op, timing, note in hw_timings:
    p_t = tf.add_paragraph()
    p_t.text = f"• {op:<25}: {timing} ({note})"
    p_t.font.name = "Calibri"
    p_t.font.size = Pt(11.5)
    p_t.font.color.rgb = TEXT_LIGHT
    p_t.space_before = Pt(4)

# Right Column: End-to-End Hardware Test
add_card(slide15, Inches(6.75), Inches(1.9), Inches(5.75), Inches(4.8), border_color=CYAN)
tb = slide15.shapes.add_textbox(Inches(6.95), Inches(2.05), Inches(5.35), Inches(4.5))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "LIVE HARDWARE TEST SEQUENCE"
p.font.name = "Arial"
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = CYAN

hw_steps = [
    ("1. WiFi Bootstrap", "ESP32-S2 auto-connects to local AP and pings Flask OTA server."),
    ("2. v1 -> v2 Update", "Fetches Manifest v1->v2 (200 B), pre-verifies in 253 ms, downloads delta (1,636 B), post-verifies, boots v2."),
    ("3. v2 -> v3 Update", "Chained update succeeds; chain head shifts to H(M_{1->2}); firmware upgraded to v3."),
    ("4. Replay Attack Injected", "Stale v1->v2 manifest transmitted to v3 device; Stage 1 Check 4 catches stale chain head -> Instant abort!"),
    ("5. Bit-Flip Injection", "Single-byte corruption in delta patch detected in Stage 2 -> Shadow slot wiped, active v3 remains pristine.")
]

for step, desc in hw_steps:
    p_s = tf.add_paragraph()
    p_s.text = f"{step}: {desc}"
    p_s.font.name = "Calibri"
    p_s.font.size = Pt(11.5)
    p_s.font.color.rgb = TEXT_LIGHT
    p_s.space_before = Pt(5)


# ==============================================================================
# SLIDE 16: COMPREHENSIVE COMPARISON TABLE
# ==============================================================================
slide16 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide16)
add_header(slide16, "15. Comparative Evaluation", "VLCDS vs. Existing State of the Art", "Systematic Feature and Security Comparison Across 8 Architectural Dimensions")

# Table Card
add_card(slide16, Inches(0.8), Inches(1.85), Inches(11.733), Inches(4.9), border_color=CYAN)
tb = slide16.shapes.add_textbox(Inches(1.0), Inches(1.95), Inches(11.333), Inches(4.7))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = f"{'Architectural Dimension':<26} | {'Samsung Patent (US10206114)':<30} | {'Base Paper (Formanek 2025)':<27} | {'VLCDS (Our Work)'}"
p.font.name = "Consolas"
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = CYAN

comp_data = [
    ("Target Platform", "Smartphones / NFC SE", "ESP32 IoT Nodes", "Constrained IoT (ESP32-S2)"),
    ("Update Unit Verified", "Monolithic Full Image Only", "Delta Patch (Unsigned)", "Delta Patch (Cryptographically Bound)"),
    ("Version Binding", "None (External metadata)", "None (Plaintext JSON)", "Cryptographic (Signed inside Manifest)"),
    ("Anti-Replay Mechanism", "Not Addressed", "System Bookkeeping", "Hash-Chain (H(prev_manifest))"),
    ("Network Channel Model", "Trusted On-Board Bus", "Untrusted Wireless Link", "Untrusted Dolev-Yao Wireless"),
    ("Pre-Verify for Deltas", "Not Supported", "Not Supported", "Yes — 200-Byte Manifest Gatekeeper"),
    ("Post-Verify Signature", "Full 2nd Signature Check", "No Signature Check", "Zero-Signature Hash Equality Check"),
    ("Physical Hardware Demo", "Phone Hardware", "ESP32 OTA Demonstration", "ESP32-S2 MicroPython Live OTA Demo")
]

for dim, sam, base, vlcds in comp_data:
    p_r = tf.add_paragraph()
    p_r.text = f"{dim:<26} | {sam:<30} | {base:<27} | {vlcds}"
    p_r.font.name = "Consolas"
    p_r.font.size = Pt(10)
    p_r.font.color.rgb = WHITE if vlcds.startswith("Constrained") or vlcds.startswith("Delta") or vlcds.startswith("Cryptographic") or vlcds.startswith("Hash-Chain") or vlcds.startswith("Yes") or vlcds.startswith("Zero") or vlcds.startswith("ESP32-S2") else TEXT_LIGHT
    p_r.space_before = Pt(4)


# ==============================================================================
# SLIDE 17: TEST SUITE & EXPERIMENTAL RESULTS
# ==============================================================================
slide17 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide17)
add_header(slide17, "16. Experimental Validation", "PyTest Test Suite & Verification Results", "13 Passing Tests Across 3 Automated Suites: 100% Attack Neutralization")

suites = [
    ("test_normal_update.py", "FUNCTIONAL TESTS (4/4 PASS)",
     "✓ test_v1_to_v2_update: Clean single update with partition swap.\n"
     "✓ test_v1_to_v2_to_v3_chain: Consecutive chained updates with hash tracking.\n"
     "✓ test_manifest_serialization: 200-byte wire binary roundtrip.\n"
     "✓ test_delta_roundtrip: Differential XOR patch generation and apply.",
     CYAN),
    ("test_attack_scenarios.py", "SECURITY TESTS (6/6 PASS)",
     "✓ test_version_mismatch: Injected v2->v3 patch to v1 node -> Aborted in Stage 1 Check 2.\n"
     "✓ test_replay_attack: Replayed accepted v1->v2 manifest -> Aborted in Stage 1 Check 4.\n"
     "✓ test_tampered_delta: Corrupted 1 bit in transit -> Aborted in Stage 2 H(delta) check.\n"
     "✓ test_tampered_manifest: Forged signature -> Aborted in Stage 1 Check 1.\n"
     "✓ test_zero_bytes_wasted: Confirmed 0 payload bytes downloaded on Stage 1 rejection.\n"
     "✓ test_zero_corruption: Confirmed active boot partition remains intact across all attacks.",
     RED),
    ("test_performance.py", "BENCHMARK TESTS (3/3 PASS)",
     "✓ test_ed25519_timings: Validated sign & verify latency under 10 ms.\n"
     "✓ test_sha256_scaling: Validated linear hash scaling from 1 KB to 1 MB.\n"
     "✓ test_protocol_overhead: Verified VLCDS overhead remains under 5% (+0.024 ms).",
     GREEN)
]

for i, (fname, ftitle, fbody, clr) in enumerate(suites):
    x = Inches(0.8 + i * 3.97)
    add_card(slide17, x, Inches(1.9), Inches(3.8), Inches(4.8), border_color=clr)
    tb = slide17.shapes.add_textbox(x + Inches(0.2), Inches(2.0), Inches(3.4), Inches(4.6))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = fname
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = clr
    
    p_t = tf.add_paragraph()
    p_t.text = ftitle
    p_t.font.name = "Arial"
    p_t.font.size = Pt(10.5)
    p_t.font.color.rgb = TEXT_MUTED
    p_t.space_before = Pt(2)
    
    p_b = tf.add_paragraph()
    p_b.text = fbody
    p_b.font.name = "Calibri"
    p_b.font.size = Pt(11)
    p_b.font.color.rgb = TEXT_LIGHT
    p_b.space_before = Pt(8)


# ==============================================================================
# SLIDE 18: CONCLUSION & FUTURE WORK
# ==============================================================================
slide18 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide18)
add_header(slide18, "17. Conclusion & Future Work", "Summary of Contributions & Research Horizons", "Delivering Provably Secure, Zero-Waste Firmware Delivery for IoT Endpoints")

# Left Column: Summary of Contributions
add_card(slide18, Inches(0.8), Inches(1.9), Inches(5.75), Inches(4.8), border_color=GREEN)
tb = slide18.shapes.add_textbox(Inches(1.0), Inches(2.05), Inches(5.35), Inches(4.5))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "SUMMARY OF ACHIEVEMENTS"
p.font.name = "Arial"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = GREEN

achievements = [
    "First protocol to unify Content Binding, State Binding, and History Binding inside a single 200-byte pre-verification manifest.",
    "Eliminates wasted bandwidth and flash write wear: Invalid or replayed updates aborted before transmitting payload bytes.",
    "Avoids redundant post-verification signature checks by binding target hash into Stage 1, incurring only +4.8% net overhead.",
    "Neutralizes 100% of Dolev-Yao network attack simulations with zero firmware corruption.",
    "Successfully demonstrated on real ESP32-S2 DevKit M1 physical hardware using pure-Python MicroPython drivers."
]

for ach in achievements:
    p_a = tf.add_paragraph()
    p_a.text = "✓ " + ach
    p_a.font.name = "Calibri"
    p_a.font.size = Pt(12)
    p_a.font.color.rgb = TEXT_LIGHT
    p_a.space_before = Pt(6)

# Right Column: Future Research Directions
add_card(slide18, Inches(6.75), Inches(1.9), Inches(5.75), Inches(4.8), border_color=AMBER)
tb = slide18.shapes.add_textbox(Inches(6.95), Inches(2.05), Inches(5.35), Inches(4.5))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "FUTURE RESEARCH HORIZONS"
p.font.name = "Arial"
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = AMBER

future_work = [
    ("Production Delta Engines", "Integrate streaming bsdiff or detools compression algorithms for multi-megabyte binary images."),
    ("Transport Confidentiality", "Pair VLCDS with lightweight OSCORE or DTLS 1.3 to guarantee patch confidentiality against eavesdroppers."),
    ("Post-Quantum Cryptography", "Evaluate NIST PQC standards (CRYSTALS-Dilithium, Falcon) for post-quantum IoT firmware authenticity."),
    ("Formal Protocol Verification", "Conduct automated formal security proofs using ProVerif or Tamarin to mathematically verify replay freedom."),
    ("Fleet Group Key Management", "Extend manifest signing to hierarchical group keys for heterogeneous industrial sensor networks.")
]

for title, desc in future_work:
    p_f = tf.add_paragraph()
    p_f.text = f"• {title}: {desc}"
    p_f.font.name = "Calibri"
    p_f.font.size = Pt(11.5)
    p_f.font.color.rgb = TEXT_LIGHT
    p_f.space_before = Pt(5)


# ==============================================================================
# SLIDE 19: TEACHER / EXAMINER Q&A REFERENCE GUIDE
# ==============================================================================
slide19 = prs.slides.add_slide(blank_layout)
set_slide_bg(slide19)
add_header(slide19, "18. Q&A Defense Guide", "Key Technical Questions & Evaluator Reference", "Anticipating Core Theoretical and Practical Defense Inquiries")

qa_items = [
    ("Q1: Why choose Ed25519 over RSA or ECDSA for IoT updates?",
     "Ed25519 (RFC 8032) provides 128-bit security with small 64-byte signatures and 32-byte public keys. Unlike RSA (requires 2048-4096 bit keys, slow verification), Ed25519 executes in ~0.38 ms on PC and ~237 ms on ESP32 without requiring hardware acceleration. Unlike ECDSA, it is immune to faulty RNG side-channel attacks because it uses deterministic nonce generation.",
     CYAN),
    ("Q2: Why not just check the signature AFTER downloading the delta patch?",
     "Downloading delta patches over constrained links (LoRa/BLE) consumes immense energy. If an update has a version mismatch or is a replayed stale patch, the device wastes 100% of the transmission time, battery power, and flash cycles. VLCDS verifies the 200-byte manifest FIRST, filtering out 100% of malicious or mismatched patches before downloading a single patch byte.",
     AMBER),
    ("Q3: Why is there no second digital signature check in Stage 3?",
     "Digital signature verification is the most computationally expensive operation. Because H(target) is already bound inside the Stage-1 manifest signature, Stage 3 only needs to compute the SHA-256 hash of the reconstructed firmware and compare 32 bytes in RAM. This provides identical cryptographic security at 1/20th the CPU cost!",
     GREEN)
]

for i, (q, a, clr) in enumerate(qa_items):
    y = Inches(1.9 + i * 1.65)
    add_card(slide19, Inches(0.8), y, Inches(11.733), Inches(1.5), border_color=clr)
    tb = slide19.shapes.add_textbox(Inches(1.0), y + Inches(0.1), Inches(11.333), Inches(1.3))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = q
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = clr
    
    p_a = tf.add_paragraph()
    p_a.text = a
    p_a.font.name = "Calibri"
    p_a.font.size = Pt(11.5)
    p_a.font.color.rgb = TEXT_LIGHT
    p_a.space_before = Pt(3)

# Save presentation
prs.save(OUTPUT_PPTX)
print(f"Presentation saved successfully to: {OUTPUT_PPTX}")

# Attempt PDF conversion via PowerPoint COM
try:
    import win32com.client
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    deck = powerpoint.Presentations.Open(OUTPUT_PPTX)
    deck.SaveAs(OUTPUT_PDF, 32) # 32 = ppSaveAsPDF
    deck.Close()
    powerpoint.Quit()
    print(f"PDF exported successfully to: {OUTPUT_PDF}")
except Exception as e:
    print(f"PowerPoint COM PDF export skipped or failed: {e}")
