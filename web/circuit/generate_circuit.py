"""
generate_circuit.py
CRT-Nano Project: High-Fidelity Virtual Circuit Schematic Diagram (1-Page PDF)
Authors: M. Dinesh Kumar (CB.AI.U4AID25126) & Malepati Venkata Sai Sujan (CB.AI.U4AID25129)
Course: 23MAT204 - Lab Exam: Frugal Healthcare AI / Edge Device Challenge
Instructor: Dr. Suman Dutta
Institution: School of AI, Amrita Vishwa Vidyapeetham
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle
import numpy as np
import os
import shutil


def generate_schematic():
    # Setup landscape A4 (11.69 x 8.27 inches)
    fig, ax = plt.subplots(figsize=(11.69, 8.27), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Color Palette: Warm technical parchment / clean blueprint
    BG_COLOR = '#FAF8F5'
    BORDER_COLOR = '#2A2825'
    TEXT_MAIN = '#1F1E1D'
    TEXT_MUTED = '#57534E'
    
    # Net Wire Colors
    COLOR_5V = '#DC2626'      # Red
    COLOR_GND = '#1C1917'     # Dark Charcoal / Black
    COLOR_ANALOG = '#059669'  # Emerald Green (PPG A0)
    COLOR_PWM = '#D97706'     # Amber (Servo D9)
    COLOR_AUDIO = '#7C3AED'   # Violet (Piezo D8)
    COLOR_TEMP = '#B45309'    # Warm Amber (Thermistor A1)
    COLOR_DIGITAL = '#64748B' # Slate (Mode D2)

    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # 1. Outer Border & Engineering Frame
    ax.add_patch(Rectangle((1.5, 1.5), 97.0, 97.0, fill=False, edgecolor=BORDER_COLOR, lw=1.6))
    ax.add_patch(Rectangle((2.3, 2.3), 95.4, 95.4, fill=False, edgecolor='#A8A29E', lw=0.6, ls='--'))

    # Subtle technical grid
    for x in range(10, 100, 10):
        ax.axvline(x, color='#E7E5E4', lw=0.4, alpha=0.6, zorder=0)
    for y in range(10, 100, 10):
        ax.axhline(y, color='#E7E5E4', lw=0.4, alpha=0.6, zorder=0)

    # 2. Top Header Banner
    ax.text(4.0, 95.2, "CRT-Nano: VIRTUAL SYSTEM CIRCUIT SCHEMATIC", fontsize=15, fontweight='bold', color=TEXT_MAIN)
    ax.text(4.0, 93.0, "Reflectance Photoplethysmography (PPG) Capillary Refill Time Measurement System | 23MAT204 Lab Exam", fontsize=9.2, color=TEXT_MUTED)

    # -------------------------------------------------------------
    # 3. Component Block: Arduino Nano V3 (Center)
    # -------------------------------------------------------------
    nano_x, nano_y, nano_w, nano_h = 36.0, 28.5, 28.0, 58.5
    ax.add_patch(FancyBboxPatch((nano_x, nano_y), nano_w, nano_h, boxstyle="round,pad=0.8,rounding_size=1.5",
                                facecolor='#F5F5F4', edgecolor='#292524', lw=1.8, zorder=2))
    
    # ATmega328P IC MCU body (centered, cleanly within pin clearances)
    ax.add_patch(FancyBboxPatch((nano_x + 7.5, nano_y + 18.0), 13.0, 18.0, boxstyle="round,pad=0.4",
                                facecolor='#292524', edgecolor='#1C1917', lw=1.2, zorder=3))
    ax.text(nano_x + 14.0, nano_y + 28.0, "ATmega328P", color='#F5F5F4', fontsize=8.5, fontweight='bold', ha='center', zorder=4)
    ax.text(nano_x + 14.0, nano_y + 24.5, "16 MHz / 5V / 32KB", color='#A8A29E', fontsize=7.0, ha='center', zorder=4)

    # Nano Header Labels
    ax.text(nano_x + 14.0, nano_y + 54.0, "ARDUINO NANO V3", color='#1C1917', fontsize=11, fontweight='bold', ha='center', zorder=4)
    ax.text(nano_x + 14.0, nano_y + 50.5, "CORE EMBEDDED CONTROLLER", color='#78716C', fontsize=7.5, ha='center', zorder=4)
    
    # Mini-USB connector port at top
    ax.add_patch(FancyBboxPatch((nano_x + 9.5, nano_y + nano_h - 1.5), 9.0, 4.2, boxstyle="round,pad=0.2",
                                facecolor='#D6D3D1', edgecolor='#44403C', lw=1.2, zorder=3))
    ax.text(nano_x + 14.0, nano_y + nano_h + 0.6, "Mini-USB (5V / UART)", fontsize=7, color='#1C1917', ha='center', fontweight='bold', zorder=4)

    # Pin Rows: Left (Analog / Power) and Right (Digital / Ground)
    left_pins = [
        ("D13", 77.0), ("3V3", 72.0), ("REF", 67.0), ("A0", 62.0),
        ("A1", 57.0),  ("A2", 52.0),  ("A3", 47.0),  ("A4", 42.0),
        ("A5", 37.0),  ("5V", 33.0),  ("RST", 29.5)
    ]
    for pin_name, py in left_pins:
        ax.add_patch(Rectangle((nano_x - 1.8, py - 1.2), 3.0, 2.4, facecolor='#E7E5E4', edgecolor='#44403C', lw=0.8, zorder=3))
        ax.text(nano_x + 2.5, py - 0.7, pin_name, fontsize=8, fontweight='bold', color=TEXT_MAIN, zorder=4)

    right_pins = [
        ("VIN", 77.0), ("GND", 72.0), ("RESET", 67.0), ("5V", 62.0),
        ("D9", 57.0),  ("D8", 52.0),  ("D7", 47.0),   ("D6", 42.0),
        ("D5", 37.0),  ("D2", 33.0),  ("GND", 29.5)
    ]
    for pin_name, py in right_pins:
        ax.add_patch(Rectangle((nano_x + nano_w - 1.2, py - 1.2), 3.0, 2.4, facecolor='#E7E5E4', edgecolor='#44403C', lw=0.8, zorder=3))
        ax.text(nano_x + nano_w - 2.5, py - 0.7, pin_name, fontsize=8, fontweight='bold', color=TEXT_MAIN, ha='right', zorder=4)

    # -------------------------------------------------------------
    # 4. Component Block: Pulse Sensor (Optical Reflectance PPG Module)
    # -------------------------------------------------------------
    ps_x, ps_y, ps_w, ps_h = 5.0, 52.0, 20.0, 31.0
    ax.add_patch(FancyBboxPatch((ps_x, ps_y), ps_w, ps_h, boxstyle="round,pad=0.5",
                                facecolor='#F0FDF4', edgecolor='#16A34A', lw=1.5, zorder=2))
    ax.text(ps_x + 10.0, ps_y + 27.5, "PULSE SENSOR", fontsize=9.5, fontweight='bold', color='#14532D', ha='center')
    ax.text(ps_x + 10.0, ps_y + 24.5, "(PPG Optical Module)", fontsize=8, color='#15803D', ha='center')
    
    # Photodiode & Green LED symbols
    ax.add_patch(Circle((ps_x + 6.5, ps_y + 16.8), 3.2, facecolor='#22C55E', edgecolor='#15803D', lw=1.0, zorder=3))
    ax.text(ps_x + 6.5, ps_y + 16.1, "LED\n565nm", color='white', fontsize=6, fontweight='bold', ha='center', zorder=4)
    
    ax.add_patch(Circle((ps_x + 13.5, ps_y + 16.8), 3.2, facecolor='#292524', edgecolor='#1C1917', lw=1.0, zorder=3))
    ax.text(ps_x + 13.5, ps_y + 16.1, "PHOTO\nDET", color='white', fontsize=6, fontweight='bold', ha='center', zorder=4)
    
    # Optical Aperture Window
    ax.add_patch(Rectangle((ps_x + 3.0, ps_y + 9.0), 14.0, 2.5, facecolor='#FEF3C7', edgecolor='#D97706', lw=0.8, ls=':', zorder=3))
    ax.text(ps_x + 10.0, ps_y + 9.8, "Fingertip Measurement Window", color='#92400E', fontsize=6.5, ha='center', zorder=4)

    # Pin Outlets on Pulse Sensor
    ax.text(ps_x + ps_w - 1.0, ps_y + 6.0, "VCC (+5V) ->", fontsize=7.5, color=COLOR_5V, fontweight='bold', ha='right')
    ax.text(ps_x + ps_w - 1.0, ps_y + 3.5, "GND ->", fontsize=7.5, color=COLOR_GND, fontweight='bold', ha='right')
    ax.text(ps_x + ps_w - 1.0, ps_y + 1.0, "SIG (Analog) ->", fontsize=7.5, color=COLOR_ANALOG, fontweight='bold', ha='right')

    # -------------------------------------------------------------
    # 5. Component Block: SG90 Micro Servo (Actuator Option)
    # -------------------------------------------------------------
    srv_x, srv_y, srv_w, srv_h = 74.0, 61.0, 22.0, 23.0
    ax.add_patch(FancyBboxPatch((srv_x, srv_y), srv_w, srv_h, boxstyle="round,pad=0.5",
                                facecolor='#FFFBEB', edgecolor='#D97706', lw=1.5, zorder=2))
    ax.text(srv_x + 11.0, srv_y + 19.5, "SG90 MICRO SERVO", fontsize=9.5, fontweight='bold', color='#78350F', ha='center')
    ax.text(srv_x + 11.0, srv_y + 16.5, "(Optional Press Actuator)", fontsize=7.5, color='#92400E', ha='center')
    
    # Motor gear circle
    ax.add_patch(Circle((srv_x + 16.0, srv_y + 9.5), 3.5, facecolor='#F59E0B', edgecolor='#B45309', lw=1.0, zorder=3))
    ax.text(srv_x + 16.0, srv_y + 8.8, "M", color='white', fontsize=8, fontweight='bold', ha='center', zorder=4)
    
    # Servo Wire Inlets
    ax.text(srv_x + 1.0, srv_y + 12.0, "<- PWM (Orange)", fontsize=7.5, color=COLOR_PWM, fontweight='bold')
    ax.text(srv_x + 1.0, srv_y + 8.0, "<- VCC (Red)", fontsize=7.5, color=COLOR_5V, fontweight='bold')
    ax.text(srv_x + 1.0, srv_y + 4.0, "<- GND (Brown)", fontsize=7.5, color=COLOR_GND, fontweight='bold')

    # -------------------------------------------------------------
    # 6. Component Block: Piezo Audio Buzzer
    # -------------------------------------------------------------
    pzo_x, pzo_y, pzo_w, pzo_h = 74.0, 36.0, 22.0, 20.0
    ax.add_patch(FancyBboxPatch((pzo_x, pzo_y), pzo_w, pzo_h, boxstyle="round,pad=0.5",
                                facecolor='#F5F3FF', edgecolor='#7C3AED', lw=1.5, zorder=2))
    ax.text(pzo_x + 11.0, pzo_y + 16.2, "PIEZO TRANSDUCER", fontsize=9.5, fontweight='bold', color='#4C1D95', ha='center')
    ax.text(pzo_x + 11.0, pzo_y + 13.5, "(Auditory Cues & Status)", fontsize=7.5, color='#6D28D9', ha='center')
    
    # Speaker Symbol
    ax.add_patch(Rectangle((pzo_x + 4.0, pzo_y + 4.0), 3.0, 5.0, facecolor='#7C3AED', edgecolor='#4C1D95', lw=0.8, zorder=3))
    speaker_poly = np.array([[pzo_x + 7.0, pzo_y + 5.0], [pzo_x + 11.5, pzo_y + 2.5], [pzo_x + 11.5, pzo_y + 10.5], [pzo_x + 7.0, pzo_y + 8.0]])
    ax.add_patch(plt.Polygon(speaker_poly, facecolor='#8B5CF6', edgecolor='#4C1D95', lw=0.8, zorder=3))
    
    # 330 Ohm resistor box
    ax.add_patch(Rectangle((pzo_x + 13.5, pzo_y + 4.5), 6.5, 4.0, facecolor='#FEF3C7', edgecolor='#B45309', lw=0.8, zorder=3))
    ax.text(pzo_x + 16.7, pzo_y + 6.5, "330Ω\nResistor", fontsize=6.2, color='#78350F', ha='center', va='center', fontweight='bold', zorder=4)

    # -------------------------------------------------------------
    # 7. Component Block: Context Extensions (Mode / Temperature)
    # -------------------------------------------------------------
    ext_x, ext_y, ext_w, ext_h = 5.0, 24.5, 22.0, 24.0
    ax.add_patch(FancyBboxPatch((ext_x, ext_y), ext_w, ext_h, boxstyle="round,pad=0.5",
                                facecolor='#F5F5F4', edgecolor='#78716C', lw=1.2, ls=':', zorder=2))
    ax.text(ext_x + 11.0, ext_y + 20.8, "OPTIONAL EXPANSION", fontsize=8.5, fontweight='bold', color=TEXT_MAIN, ha='center')

    # Pushbutton D2
    ax.add_patch(Rectangle((ext_x + 1.5, ext_y + 10.5), 8.5, 7.5, facecolor='#E7E5E4', edgecolor='#44403C', lw=0.8, zorder=3))
    ax.add_patch(Circle((ext_x + 5.7, ext_y + 14.2), 2.0, facecolor='#EF4444', edgecolor='#B91C1C', lw=0.8, zorder=4))
    ax.text(ext_x + 5.7, ext_y + 8.0, "D2 Tactile Switch\n(Mode Select)", fontsize=6.2, ha='center', color=TEXT_MAIN)

    # Thermistor Divider A1
    ax.add_patch(Rectangle((ext_x + 11.5, ext_y + 10.5), 9.0, 7.5, facecolor='#FEF3C7', edgecolor='#D97706', lw=0.8, zorder=3))
    ax.text(ext_x + 16.0, ext_y + 14.8, "NTC 10kΩ\n+10kΩ Ref", fontsize=6.2, ha='center', color='#92400E', fontweight='bold')
    ax.text(ext_x + 16.0, ext_y + 8.0, "A1 Finger Temp\nDivider Midpoint", fontsize=6.2, ha='center', color=TEXT_MAIN)

    # -------------------------------------------------------------
    # 8. Decoupling Capacitors Block (Dedicated region between Nano & bottom panels)
    # -------------------------------------------------------------
    ax.add_patch(FancyBboxPatch((39.0, 21.8), 22.0, 5.0, boxstyle="round,pad=0.3",
                                facecolor='#FEF2F2', edgecolor='#DC2626', lw=0.9, ls='--', zorder=2))
    ax.text(50.0, 24.8, "DC Rail Decoupling Filter", fontsize=7.5, color='#991B1B', fontweight='bold', ha='center')
    ax.text(50.0, 22.8, "10µF (Electrolytic) + 0.1µF (Ceramic)", fontsize=6.5, color='#7F1D1D', ha='center')

    # -------------------------------------------------------------
    # 9. Wiring Nets (Clean routing with clear clearance)
    # -------------------------------------------------------------
    # Signal A0: Pulse Sensor SIG (x=25, y=53.0) -> Nano A0 (x=36, y=62)
    ax.plot([25.0, 30.5, 30.5, 34.2], [53.0, 53.0, 62.0, 62.0], color=COLOR_ANALOG, lw=2.2, zorder=5)
    ax.text(28.0, 58.5, "PPG A0", color=COLOR_ANALOG, fontsize=7.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle='square,pad=0.15', facecolor='#ECFDF5', edgecolor=COLOR_ANALOG, lw=0.6))

    # Signal D9: Servo PWM (x=64, y=57) -> Servo SIG (x=74, y=73)
    ax.plot([65.8, 70.0, 70.0, 74.0], [57.0, 57.0, 73.0, 73.0], color=COLOR_PWM, lw=2.2, zorder=5)
    ax.text(68.5, 66.5, "PWM D9", color=COLOR_PWM, fontsize=7.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle='square,pad=0.15', facecolor='#FFFBEB', edgecolor=COLOR_PWM, lw=0.6))

    # Signal D8: Audio Out (x=64, y=52) -> Piezo Input (x=74, y=49)
    ax.plot([65.8, 70.0, 70.0, 74.0], [52.0, 52.0, 49.0, 49.0], color=COLOR_AUDIO, lw=2.2, zorder=5)
    ax.text(68.5, 50.8, "TONE D8", color=COLOR_AUDIO, fontsize=7.5, fontweight='bold', ha='center',
            bbox=dict(boxstyle='square,pad=0.15', facecolor='#F5F3FF', edgecolor=COLOR_AUDIO, lw=0.6))

    # 5V Power Distribution (RED)
    # Nano 5V pin (x=36, y=33) -> Filter Bus (x=39, y=24.3)
    ax.plot([34.2, 31.5, 31.5, 39.0], [33.0, 33.0, 24.3, 24.3], color=COLOR_5V, lw=2.0, zorder=5)
    ax.plot([31.5, 31.5, 25.0], [33.0, 58.0, 58.0], color=COLOR_5V, lw=2.0, zorder=5) # to PPG VCC
    ax.plot([61.0, 71.5, 71.5, 74.0], [24.3, 24.3, 69.0, 69.0], color=COLOR_5V, lw=2.0, zorder=5) # to Servo VCC
    ax.plot([31.5], [33.0], marker='o', markersize=4.5, color=COLOR_5V, zorder=6)

    # GND Distribution (DARK CHARCOAL)
    # Nano GND pin (x=64, y=72) -> Common Ground
    ax.plot([65.8, 72.5, 72.5, 74.0], [72.0, 72.0, 65.0, 65.0], color=COLOR_GND, lw=2.0, zorder=5) # to Servo GND
    ax.plot([72.5, 72.5, 74.0], [65.0, 40.5, 40.5], color=COLOR_GND, lw=2.0, zorder=5) # to Piezo GND
    # PPG GND to Nano GND (bottom pin x=64, y=29.5)
    ax.plot([25.0, 29.0, 29.0, 39.0], [55.5, 55.5, 19.5, 19.5], color=COLOR_GND, lw=1.8, zorder=5)
    ax.plot([61.0, 68.0, 68.0, 65.8], [19.5, 19.5, 29.5, 29.5], color=COLOR_GND, lw=1.8, zorder=5)

    # Mode D2 and Temp A1 Net Hints
    ax.plot([34.2, 28.0, 28.0, 25.0], [57.0, 57.0, 35.0, 35.0], color=COLOR_TEMP, lw=1.2, ls=':', zorder=4)
    ax.plot([65.8, 68.5, 68.5, 15.0], [33.0, 33.0, 24.5, 24.5], color=COLOR_DIGITAL, lw=1.2, ls=':', zorder=4)

    # -------------------------------------------------------------
    # 10. Information Panels: Pin Mapping & Bill of Materials
    # -------------------------------------------------------------
    # Pin Map Box (Bottom Left: y=3.0 to y=19.5)
    ax.add_patch(FancyBboxPatch((3.5, 3.0), 41.0, 16.5, boxstyle="round,pad=0.3",
                                facecolor='#FFFFFF', edgecolor='#D6D3D1', lw=1.0, zorder=2))
    ax.text(4.5, 17.8, "PIN ASSIGNMENT & SUBSYSTEM ROUTING", fontsize=8.2, fontweight='bold', color=TEXT_MAIN)
    table_text = (
        "Pin A0   -> Optical Sensor Analog Out (PPG Reflectance)\n"
        "Pin D8   -> Piezo Acoustic Transducer (+) via 330Ω Limiter\n"
        "Pin D9   -> SG90 Servo Actuator PWM (Position Command)\n"
        "Pin D2   -> Mode Pushbutton (Internal Pull-Up to GND)\n"
        "Pin A1   -> Optional NTC 10kΩ Thermistor (Temperature Context)\n"
        "5V Rail  -> Common 5V Supply Rail (10µF + 0.1µF Decoupled)\n"
        "GND Rail -> Star-Ground Reference Bus"
    )
    ax.text(4.5, 4.2, table_text, fontsize=6.8, color=TEXT_MUTED, family='monospace', linespacing=1.35)

    # Bill of Materials & Cost Box (Bottom Middle: y=3.0 to y=19.5)
    ax.add_patch(FancyBboxPatch((46.0, 3.0), 26.0, 16.5, boxstyle="round,pad=0.3",
                                facecolor='#FFFFFF', edgecolor='#D6D3D1', lw=1.0, zorder=2))
    ax.text(47.0, 17.8, "BILL OF MATERIALS & COST (INR)", fontsize=8.2, fontweight='bold', color=TEXT_MAIN)
    bom_text = (
        "• Arduino Nano V3 (CH340)   : Rs. 155\n"
        "• PPG Pulse Sensor Module   : Rs.  75\n"
        "• Piezo Acoustic Disc       : Rs.  12\n"
        "• Premium Jumper Wires      : Rs.  35\n"
        "• Carbon Film Resistor Pack : Rs.  10\n"
        "-------------------------------------\n"
        "CORE MANUAL CONFIG          : Rs. 287\n"
        "With SG90 Micro Servo (+Rs70): Rs. 357\n"
        "[Target T6 <= Rs. 360: FULLY COMPLIANT]"
    )
    ax.text(47.0, 4.0, bom_text, fontsize=6.6, color=TEXT_MUTED, family='monospace', linespacing=1.28)

    # -------------------------------------------------------------
    # 11. Engineering Title Block (Bottom Right Corner: y=3.0 to y=19.5)
    # -------------------------------------------------------------
    tb_x, tb_y, tb_w, tb_h = 73.5, 3.0, 23.5, 16.5
    ax.add_patch(FancyBboxPatch((tb_x, tb_y), tb_w, tb_h, boxstyle="square,pad=0.0",
                                facecolor='#F5F5F4', edgecolor='#292524', lw=1.5, zorder=2))
    ax.add_patch(Rectangle((tb_x, tb_y + 12.0), tb_w, 4.5, facecolor='#292524', edgecolor='#292524', zorder=3))
    ax.text(tb_x + 11.75, tb_y + 14.4, "AMRITA SCHOOL OF AI", color='#FFFFFF', fontsize=8.2, fontweight='bold', ha='center', zorder=4)
    ax.text(tb_x + 11.75, tb_y + 12.6, "23MAT204 - Healthcare AI / Edge Challenge", color='#D6D3D1', fontsize=6.0, ha='center', zorder=4)

    meta_text = (
        "PROJECT : CRT-Nano (Capillary Refill)\n"
        "STUDENT 1: M. Dinesh Kumar (25126)\n"
        "STUDENT 2: M. V. Sai Sujan (25129)\n"
        "INSTRUCTOR: Dr. Suman Dutta\n"
        "REVISION : v2.4 (Virtual Schematic)\n"
        "DATE     : October 30, 2026\n"
        "SHEET    : 1 OF 1 (Single Page PDF)"
    )
    ax.text(tb_x + 1.2, tb_y + 0.8, meta_text, fontsize=6.3, color='#1C1917', family='monospace', linespacing=1.35, zorder=4)

    plt.tight_layout()
    
    # Save as 1-Page PDF and high-res image formats
    pdf_path = "circuit/CRT_Nano_Virtual_Circuit_Diagram.pdf"
    png_path = "circuit/circuit_diagram.png"
    svg_path = "circuit/circuit_diagram.svg"
    
    plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
    plt.savefig(png_path, format='png', dpi=300, bbox_inches='tight')
    plt.savefig(svg_path, format='svg', bbox_inches='tight')
    plt.close()
    
    # Copy to root directory for immediate single-click access
    shutil.copyfile(pdf_path, "CRT_Nano_Virtual_Circuit_Diagram.pdf")
    
    print(f"Generated schematic PDF: {pdf_path} (copied to root)")
    print(f"Generated schematic PNG: {png_path}")
    print(f"Generated schematic SVG: {svg_path}")


if __name__ == '__main__':
    generate_schematic()
