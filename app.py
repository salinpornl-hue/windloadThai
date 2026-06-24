import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# ==========================================
# ฐานข้อมูลพื้นฐาน มยผ. 1311-50
# ==========================================
PROVINCE_V = {
    "กรุงเทพฯ / นนทบุรี / ปทุมธานี / สมุทรปราการ / สมุทรสาคร": 25.0,
    "ชลบุรี / ระยอง / จันทบุรี / ตราด": 30.0,
    "ภูเก็ต / พังงา / กระบี่": 27.0,
    "เชียงใหม่ / เชียงราย / พิษณุโลก / แม่ฮ่องสอน": 25.0,
    "นครราชสีมา / ขอนแก่น / อุดรธานี / อุบลราชธานี": 25.0,
    "สงขลา / สุราษฎร์ธานี / นครศรีธรรมราช": 25.0,
    "🛠️ กำหนดค่าความเร็วลมเอง (Manual Input)": 0.0,
}

# ข้อมูลค่าพารามิเตอร์ตามสภาพภูมิประเทศ (มยผ. 1311-50 ตารางที่ 1 และภาคผนวก ค)
EXPOSURE_PARAMS = {
    'A': {'alpha': 0.20, 'ce_min': 0.9, 'ce_max': 1.5,
          'c': 0.30, 'ell': 98.0,  'epsilon': 0.33, 'alpha_bar': 0.15, 'b_bar': 0.65,
          'label': 'A (โล่งแจ้ง / ชายฝั่งทะเล)'},
    'B': {'alpha': 0.28, 'ce_min': 0.7, 'ce_max': 1.2,
          'c': 0.20, 'ell': 152.0, 'epsilon': 0.25, 'alpha_bar': 0.25, 'b_bar': 0.45,
          'label': 'B (ชานเมือง / ต้นไม้หนาแน่น)'},
    'C': {'alpha': 0.40, 'ce_min': 0.5, 'ce_max': 1.0,
          'c': 0.15, 'ell': 198.0, 'epsilon': 0.20, 'alpha_bar': 0.35, 'b_bar': 0.30,
          'label': 'C (ในเมือง / อาคารสูงโดยรอบ)'},
}

# ==========================================
# ฟังก์ชันหลักการคำนวณ (ตรวจสอบความถูกต้องแล้ว)
# ==========================================

def get_exposure_key(exposure_str):
    """แยกประเภทสภาพภูมิประเทศจาก string"""
    for k in EXPOSURE_PARAMS:
        if k in exposure_str:
            return k
    return 'B'

def calculate_q(V):
    """
    คำนวณแรงลมอ้างอิงพื้นฐาน (Basic Wind Pressure)
    สูตร: q = (0.5 × ρ × V²) / g
    ρ = 1.25 kg/m³ (ความหนาแน่นอากาศมาตรฐาน)
    g = 9.80665 m/s² (ความเร่งเนื่องจากแรงโน้มถ่วง)
    หน่วยผล: kgf/m²
    อ้างอิง: มยผ. 1311-50 สมการที่ 3.1
    """
    return (0.5 * 1.25 * (V ** 2)) / 9.80665

def get_Ce(z, exp_key):
    """
    คำนวณสัมประสิทธิ์ความสูงและสภาพภูมิประเทศ Ce
    สูตร: Ce = (z_eff / 10)^alpha  อยู่ในช่วง [Ce_min, Ce_max]
    z_eff = max(z, 6.0 ม.)  (ความสูงต่ำสุดอ้างอิง 6.0 ม.)
    อ้างอิง: มยผ. 1311-50 ตารางที่ 1 / สมการที่ 3.2
    """
    p = EXPOSURE_PARAMS[exp_key]
    z_eff = max(z, 6.0)
    raw = (z_eff / 10.0) ** p['alpha']
    ce = min(max(raw, p['ce_min']), p['ce_max'])
    return ce, z_eff, raw

def calculate_dynamic_cg(H, B_dim, L_dim, T1, damping, exp_key, V):
    """
    คำนวณสัมประสิทธิ์ลมกระโชกแบบพลศาสตร์ Cg สำหรับอาคารสูง/เพรียว
    อ้างอิง: มยผ. 1311-50 หมวด 4 (Dynamic Gust Factor Method - NBCC based)

    นิยามตัวแปร:
      H     = ความสูงอาคาร (ม.)
      B_dim = มิติอาคารขนานทิศลม (ม.) — ใช้คำนวณ η_L
      L_dim = มิติอาคารตั้งฉากทิศลม (ม.) — ใช้คำนวณ Q, η_B

    ผลลัพธ์: Cg ≥ 1.5 (ค่าต่ำสุดตามมาตรฐาน)
    """
    p = EXPOSURE_PARAMS[exp_key]
    n1 = 1.0 / T1  # ความถี่ธรรมชาติขั้นพื้นฐาน (Hz)
    
    # ความสูงอ้างอิงเฉลี่ย: z̄ = 0.6H ≥ 4.5 ม.
    z_bar = max(0.6 * H, 4.5)

    # 1) ความเข้มปั่นป่วน I(z̄)  —  มยผ. สมการ 4.3
    Iz_bar = p['c'] * ((10.0 / z_bar) ** (1.0 / 6.0))

    # 2) สเกลความปั่นป่วน L(z̄)  —  มยผ. สมการ 4.4
    Lz_bar = p['ell'] * ((z_bar / 10.0) ** p['epsilon'])

    # 3) ตัวประกอบพื้นหลัง Q (Background turbulence)  —  มยผ. สมการ 4.5
    #    L_dim คือมิติตั้งฉากลม (width ของผิวด้านรับลม)
    Q = math.sqrt(1.0 / (1.0 + 0.63 * (((L_dim + H) / Lz_bar) ** 0.63)))

    # 4) ความเร็วลมเฉลี่ยที่ z̄  —  มยผ. สมการ 4.6
    V_bar_z = p['b_bar'] * ((z_bar / 10.0) ** p['alpha_bar']) * V

    # 5) ความถี่ไร้มิติ N1  —  มยผ. สมการ 4.7
    N1 = (n1 * Lz_bar) / V_bar_z if V_bar_z > 0 else 0.1

    # 6) สเปกตรัมลม Rn  —  มยผ. สมการ 4.8
    Rn = (7.47 * N1) / ((1.0 + 10.3 * N1) ** (5.0 / 3.0))

    # 7) ตัวประกอบขนาด η และ R  —  มยผ. สมการ 4.9–4.11
    eta_h = (4.6 * n1 * H)     / V_bar_z if V_bar_z > 0 else 0.1   # แนวตั้ง
    eta_B = (4.6 * n1 * L_dim) / V_bar_z if V_bar_z > 0 else 0.1   # แนวนอน ⊥ ลม
    eta_L = (15.4 * n1 * B_dim) / V_bar_z if V_bar_z > 0 else 0.1  # แนวนอน ∥ ลม

    def size_reduction(eta):
        if eta <= 1e-6:
            return 1.0
        return (1.0 / eta) - (1.0 / (2.0 * eta**2)) * (1.0 - math.exp(-2.0 * eta))

    Rh = size_reduction(eta_h)
    RB = size_reduction(eta_B)
    RL = size_reduction(eta_L)

    # ตัวประกอบการตอบสนองแบบสั่นพ้อง R  —  มยผ. สมการ 4.10
    R = math.sqrt((1.0 / damping) * Rn * Rh * RB * (0.53 + 0.47 * RL))

    # 8) Peak factors
    g_q = 3.4   # ตัวประกอบยอดแรงลมพื้นหลัง
    g_v = 3.4   # (ไม่ได้ใช้แยก แต่โดยปกติ = gq)
    log_term = math.log(3600.0 * n1)
    g_r = math.sqrt(2.0 * log_term) + (0.577 / math.sqrt(2.0 * log_term))  # มยผ. สมการ 4.12

    # 9) Cg แบบพลศาสตร์  —  มยผ. สมการ 4.1
    #    Cg = 1 + 2·Iz̄·√[(gq·Q)² + (gr·R)²]
    #    (สำหรับอาคารแกร่ง: Cg = 1 + 2·gq·Iz̄·Q  แต่ R=0)
    Cg_dyn = 1.0 + 2.0 * Iz_bar * math.sqrt((g_q * Q)**2 + (g_r * R)**2)
    Cg_final = max(Cg_dyn, 1.5)   # ค่าต่ำสุด 1.5 ตามมาตรฐาน

    details = {
        'z_bar': z_bar, 'Iz_bar': Iz_bar, 'Lz_bar': Lz_bar, 'Q': Q,
        'V_bar_z': V_bar_z, 'N1': N1, 'Rn': Rn,
        'eta_h': eta_h, 'eta_B': eta_B, 'eta_L': eta_L,
        'Rh': Rh, 'RB': RB, 'RL': RL, 'R': R,
        'g_q': g_q, 'g_r': g_r, 'n1': n1,
        'Cg_dyn': Cg_dyn,
    }
    return Cg_final, details


# ==========================================
# Streamlit UI Setup
# ==========================================
st.set_page_config(page_title="Wind Load Analyzer Pro V4.0", layout="wide", page_icon="🌪️")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans Thai', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #0F2557 0%, #1E40AF 60%, #1D6FC4 100%);
    padding: 22px 28px; border-radius: 12px; margin-bottom: 18px;
    box-shadow: 0 4px 20px rgba(30,64,175,0.25);
}
.main-header h1 { color: #fff; font-size: 1.85rem; font-weight: 700; margin: 0 0 4px 0; letter-spacing: -0.5px; }
.main-header p  { color: #93C5FD; margin: 0; font-size: 0.92rem; }

.metric-card {
    background: #fff; border: 1px solid #E2E8F0; border-radius: 10px;
    padding: 14px 16px; text-align: center;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
}
.metric-card .label { font-size: 0.78rem; color: #64748B; font-weight: 500; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.04em; }
.metric-card .value { font-size: 1.6rem; font-weight: 700; color: #1E3A8A; line-height: 1.1; }
.metric-card .unit  { font-size: 0.78rem; color: #94A3B8; margin-top: 2px; }

.section-title {
    font-size: 1.05rem; font-weight: 700; color: #1E3A8A;
    border-left: 4px solid #3B82F6; padding-left: 10px;
    margin: 18px 0 10px 0;
}

.calc-block {
    background: #F8FAFF; border: 1px solid #DBEAFE;
    border-radius: 8px; padding: 14px 18px; margin: 8px 0;
}
.calc-block .step-label {
    font-size: 0.78rem; font-weight: 700; color: #2563EB;
    text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;
}

.result-highlight {
    background: #EFF6FF; border-left: 4px solid #2563EB;
    border-radius: 0 8px 8px 0; padding: 10px 16px; margin: 6px 0;
    font-size: 0.96rem;
}

.warning-box {
    background: #FFFBEB; border: 1px solid #F59E0B;
    border-radius: 8px; padding: 12px 16px; margin: 8px 0;
}
.info-box {
    background: #F0FDF4; border: 1px solid #22C55E;
    border-radius: 8px; padding: 12px 16px; margin: 8px 0;
}
.verdict-wind  { background:#FEF2F2; border-left: 5px solid #EF4444; padding:14px 18px; border-radius:0 10px 10px 0; }
.verdict-quake { background:#EFF6FF; border-left: 5px solid #3B82F6; padding:14px 18px; border-radius:0 10px 10px 0; }

.floor-card {
    background: #fff; border:1px solid #E5E7EB; border-radius:8px;
    padding: 12px 16px; margin:6px 0;
}
.floor-card h4 { color:#1E3A8A; font-size:0.95rem; font-weight:700; margin:0 0 8px 0; }

.ref-badge {
    display: inline-block; background: #EFF6FF; color: #1D4ED8;
    font-size: 0.72rem; font-weight: 600; padding: 2px 8px; border-radius: 20px;
    border: 1px solid #BFDBFE; margin-left: 6px;
}
.formula-note { font-size:0.83rem; color:#6B7280; font-style:italic; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
  <h1>🌪️ Wind Load Analyzer Pro V4.0</h1>
  <p>ระบบวิเคราะห์แรงลมแบบพลศาสตร์, แผนภาพ 3D, และรายการคำนวณสมบูรณ์ตาม <strong>มยผ. 1311-50</strong></p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("## ⚙️ ข้อกำหนดการออกแบบ")
    
    st.markdown("### 1 · ข้อมูลแรงลมและภูมิประเทศ")
    prov_list = list(PROVINCE_V.keys())
    prov_choice = st.selectbox("จังหวัด / ความเร็วลมพื้นที่", prov_list)
    V_table = PROVINCE_V[prov_choice]
    if V_table == 0.0:
        V_input = st.number_input("ความเร็วลม V (m/s)", value=25.0, min_value=10.0, max_value=80.0, step=1.0)
    else:
        V_input = V_table
        st.info(f"V = **{V_input:.0f} m/s**")

    exp_labels = [v['label'] for v in EXPOSURE_PARAMS.values()]
    exp_choice = st.selectbox("สภาพภูมิประเทศ", exp_labels, index=1)
    exp_key = get_exposure_key(exp_choice)

    Ct_input = st.number_input("ตัวคูณภูมิประเทศ Ct (เนิน/หน้าผา)", value=1.00, min_value=1.0, max_value=1.5, step=0.01,
                                help="ปกติ Ct = 1.0 สำหรับพื้นที่ราบ กรณีเนินเขาให้คำนวณตาม มยผ. หมวด 3.4")
    Iw_input = st.selectbox("ค่าความสำคัญ Iw", [("อาคารทั่วไป (Iw = 1.00)", 1.0),
                                                   ("อาคารสำคัญมาก (Iw = 1.15)", 1.15)],
                             format_func=lambda x: x[0])[1]

    st.markdown("---")
    st.markdown("### 2 · การวิเคราะห์ Gust Effect (Cg)")
    gust_mode = st.radio("ประเภทการตอบสนองโครงสร้าง",
                          ["อาคารแข็งเกร็ง (Rigid: Cg = 2.0)",
                           "อาคารสูง/เพรียว (Flexible: Dynamic Cg)"])
    if "Flexible" in gust_mode:
        T1_input    = st.number_input("คาบสั่นธรรมชาติ T₁ (วินาที)", value=1.20, min_value=0.10, step=0.05,
                                       help="สำหรับอาคารคอนกรีต: T₁ ≈ 0.05 × H^(3/4), เหล็ก: T₁ ≈ 0.085 × H^(3/4)")
        damp_input  = st.number_input("อัตราส่วนความหน่วง β", value=0.020, min_value=0.005, max_value=0.050,
                                       step=0.005, format="%.3f",
                                       help="คอนกรีต: β ≈ 0.02–0.05, เหล็ก: β ≈ 0.01–0.02")
    else:
        T1_input = 0.5
        damp_input = 0.02

    st.markdown("---")
    st.markdown("### 3 · สัมประสิทธิ์แรงดัน (Cp)")
    enclosure = st.selectbox("ลักษณะการปิดล้อม",
                              ["อาคารปิดทึบ (Enclosed: GCpi = ±0.18)",
                               "อาคารปิดล้อมบางส่วน (Partially: GCpi = ±0.55)"])
    GCpi_val = 0.55 if "Partially" in enclosure else 0.18

    Cp_w = st.number_input("Cp ผนังรับลม (Windward, +)", value=0.80, step=0.05,
                            help="มยผ. ตารางที่ 2: อาคารสี่เหลี่ยมทั่วไป Cp_w = +0.8")
    Cp_l = st.number_input("Cp ผนังตามลม (Leeward, −)", value=-0.50, step=0.05,
                            help="มยผ. ตารางที่ 2: Cp_l ขึ้นกับ L/B ratio, ทั่วไป −0.3 ถึง −0.5")
    
    st.markdown("**หลังคา**")
    roof_type = st.radio("ประเภทหลังคา", ["แบน (Flat Roof)", "จั่ว / เพิงแหงน (Gable/Shed Roof)"])
    if "แบน" in roof_type:
        Cp_r = st.number_input("Cp หลังคาแบน (uplift, −)", value=-0.70, step=0.05)
        roof_angle_deg = 0.0
    else:
        roof_angle_deg = st.number_input("ความชันหลังคา (°)", value=15.0, min_value=0.0, max_value=45.0, step=1.0)
        Cp_r_w = st.number_input("Cp หลังคาฝั่งรับลม", value=-0.90, step=0.05)
        Cp_r_l = st.number_input("Cp หลังคาฝั่งตามลม", value=-0.50, step=0.05)

    st.markdown("---")
    st.markdown("### 4 · แรงแผ่นดินไหว (Base Shear)")
    eq_mode = st.radio("วิธีคำนวณ V_EQ",
                        ["ประมาณการ Equivalent Static", "ระบุค่าเอง (kN)"])
    if "ประมาณ" in eq_mode:
        w_per_m2  = st.number_input("น้ำหนักต่อพื้นที่ชั้น (kgf/m²)", value=600.0, step=50.0,
                                     help="รวม DL + 0.25LL โดยประมาณ")
        Cs_coeff  = st.number_input("สัมประสิทธิ์แผ่นดินไหว Cs", value=0.050, step=0.005, format="%.3f")
    else:
        V_EQ_manual = st.number_input("ระบุ V_EQ (kN)", value=120.0, step=10.0)

# ==========================================
# MAIN AREA: ข้อมูลมิติอาคาร
# ==========================================
st.markdown('<div class="section-title">🏢 มิติรูปทรงอาคาร</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    B = st.number_input("B — ความกว้างขนานลม (ม.)", value=15.0, min_value=1.0,
                         help="มิติตึกวัดตามทิศทางลม (along-wind depth)")
with c2:
    L = st.number_input("L — ความยาวตั้งฉากลม (ม.)", value=20.0, min_value=1.0,
                         help="มิติตึกวัดตั้งฉากทิศลม (across-wind width) — เป็นความกว้างผิวด้านรับลม")
with c3:
    num_stories = st.number_input("จำนวนชั้น", value=3, min_value=1, max_value=50)

with st.expander("📐 ความสูงรายชั้น", expanded=True):
    cols = st.columns(min(num_stories, 5))
    floor_heights = []
    for i in range(num_stories):
        default_h = 4.0 if i == 0 else 3.5
        hv = cols[i % 5].number_input(f"ชั้น {i+1} (ม.)", value=default_h, min_value=1.0,
                                       key=f"fh_{i}", step=0.1)
        floor_heights.append(hv)
H_total = sum(floor_heights)

# ความสูงสันหลังคา
if "จั่ว" in roof_type:
    h_ridge = (B / 2.0) * math.tan(math.radians(roof_angle_deg))
else:
    h_ridge = 0.0

# ==========================================
# ENGINE: คำนวณหลัก
# ==========================================

# 1. แรงลมพื้นฐาน
q = calculate_q(V_input)

# 2. Cg
if "Flexible" in gust_mode:
    Cg_used, dyn_det = calculate_dynamic_cg(H_total, B, L, T1_input, damp_input, exp_key, V_input)
else:
    Cg_used = 2.0
    dyn_det = None

# 3. แรงดันที่ระดับหลังคา qh
Ce_H, z_eff_H, raw_Ce_H = get_Ce(H_total, exp_key)
qh = q * Ce_H * Ct_input

# 4. แรงดันท้ายลม (ใช้ Ce ที่ H คงที่)
p_leeward_ext = Iw_input * qh * Cg_used * Cp_l   # kgf/m²

# 5. แรงดันภายใน
p_int_pos = qh * GCpi_val    # +GCpi (ดันออก)
p_int_neg = -(qh * GCpi_val) # −GCpi (ดูดเข้า)

# กรณีประกอบ
net_l_c1 = p_leeward_ext - p_int_neg  # Case 1: leeward − (−GCpi) = ผลรวมสูงสุด (โดยมาก ≤ 0)
net_l_c2 = p_leeward_ext - p_int_pos  # Case 2: leeward − (+GCpi)

# 6. หลังคา
if "แบน" in roof_type:
    p_roof_ext = Iw_input * qh * Cg_used * Cp_r
    net_roof_c1 = p_roof_ext - p_int_neg
    net_roof_c2 = p_roof_ext - p_int_pos
    F_roof_horiz = 0.0   # หลังคาแบนไม่มีแรงแนวราบสุทธิ
else:
    p_roof_w_ext = Iw_input * qh * Cg_used * Cp_r_w
    p_roof_l_ext = Iw_input * qh * Cg_used * Cp_r_l
    area_roof_vert = h_ridge * L   # พื้นที่ฉายของหน้าจั่ว (แนวตั้ง)
    F_roof_horiz = (p_roof_w_ext - p_roof_l_ext) * area_roof_vert * 0.00980665   # kN

# 7. คำนวณรายชั้น
z_cum = 0.0
floors_data = []
for i in range(num_stories):
    h   = floor_heights[i]
    z_b = z_cum
    z_t = z_cum + h
    z_m = (z_b + z_t) / 2.0

    Ce_m, z_eff_m, raw_Ce_m = get_Ce(z_m, exp_key)
    q_z = q * Ce_m * Ct_input    # แรงลมอ้างอิงที่ความสูง z (kgf/m²)
    p_w_ext = Iw_input * q_z * Cg_used * Cp_w

    net_w_c1 = p_w_ext - p_int_neg   # +GCpi inside → ลด
    net_w_c2 = p_w_ext - p_int_pos   # −GCpi inside → เพิ่ม

    A_front = L * h    # พื้นที่ผิวด้านรับลม = L (ตั้งฉากลม) × h

    F_to_kN = 0.00980665   # kgf → kN conversion (1 kgf = 9.80665 N = 0.00980665 kN)

    F_w_ext  = p_w_ext * A_front * F_to_kN
    F_w_c1   = net_w_c1 * A_front * F_to_kN
    F_w_c2   = net_w_c2 * A_front * F_to_kN
    F_l_ext  = p_leeward_ext * A_front * F_to_kN
    F_l_c1   = net_l_c1 * A_front * F_to_kN
    F_l_c2   = net_l_c2 * A_front * F_to_kN

    # แรงเฉือนสุทธิแนวราบของชั้น (Net Storey Shear contribution)
    F_net_ext = F_w_ext - F_l_ext
    F_net_c1  = F_w_c1  - F_l_c1    # = F_net_ext (GCpi cancels for enclosed building net shear)
    F_net_c2  = F_w_c2  - F_l_c2    # = F_net_ext

    floors_data.append(dict(
        floor=i+1, h=h, z_bot=z_b, z_top=z_t, z_mid=z_m,
        z_eff_m=z_eff_m, raw_Ce_m=raw_Ce_m, Ce_m=Ce_m,
        q_z=q_z, p_w_ext=p_w_ext, net_w_c1=net_w_c1, net_w_c2=net_w_c2,
        A_front=A_front,
        F_w_ext=F_w_ext, F_w_c1=F_w_c1, F_w_c2=F_w_c2,
        F_l_ext=F_l_ext, F_l_c1=F_l_c1, F_l_c2=F_l_c2,
        F_net_ext=F_net_ext, F_net_c1=F_net_c1, F_net_c2=F_net_c2,
    ))
    z_cum = z_t

# Base shear รวม
V_wind = sum(f['F_net_ext'] for f in floors_data) + F_roof_horiz

# แผ่นดินไหว
if "ประมาณ" in eq_mode:
    # น้ำหนักอาคาร W = พื้นที่ × ความสูงรวม (ต่อชั้น) × น้ำหนักต่อ m²
    W_total = (B * L) * H_total * w_per_m2 * 0.00980665  # kN (approx: W = sum_floors(A*w))
    V_EQ_calc = Cs_coeff * W_total
else:
    V_EQ_calc = V_EQ_manual

# ==========================================
# VISUALIZATION FUNCTIONS
# ==========================================
def make_3d_figure():
    fig = go.Figure()

    # --- Building box ---
    xs = [0, B, B, 0, 0, B, B, 0]
    ys = [0, 0, L, L, 0, 0, L, L]
    zs = [0, 0, 0, 0, H_total, H_total, H_total, H_total]
    if "จั่ว" in roof_type:
        xs += [B/2, B/2]; ys += [0, L]; zs += [H_total+h_ridge, H_total+h_ridge]

    fig.add_trace(go.Mesh3d(x=xs, y=ys, z=zs, alphahull=0,
                             opacity=0.12, color='#3B82F6', name='อาคาร'))

    # wireframe
    lc = dict(color='#1E3A8A', width=2.5)
    for zz in [0, H_total]:
        fig.add_trace(go.Scatter3d(x=[0,B,B,0,0], y=[0,0,L,L,0], z=[zz]*5,
                                    mode='lines', line=lc, showlegend=False))
    for xi, yi in zip([0,B,B,0],[0,0,L,L]):
        fig.add_trace(go.Scatter3d(x=[xi,xi], y=[yi,yi], z=[0,H_total],
                                    mode='lines', line=lc, showlegend=False))
    if "จั่ว" in roof_type:
        for yy in [0, L]:
            fig.add_trace(go.Scatter3d(x=[0,B/2,B], y=[yy,yy,yy],
                                        z=[H_total,H_total+h_ridge,H_total],
                                        mode='lines', line=lc, showlegend=False))
        fig.add_trace(go.Scatter3d(x=[B/2,B/2], y=[0,L],
                                    z=[H_total+h_ridge,H_total+h_ridge],
                                    mode='lines', line=lc, showlegend=False))

    # Floor level lines
    z_cum2 = 0
    for fd in floors_data:
        z_cum2 += fd['h']
        fig.add_trace(go.Scatter3d(x=[0,B,B,0,0], y=[0,0,L,L,0],
                                    z=[z_cum2]*5, mode='lines',
                                    line=dict(color='#94A3B8', width=1, dash='dot'),
                                    showlegend=False))

    # Wind arrow cones
    scale = max(B, L, H_total)
    wy_pts = [L*0.2, L*0.5, L*0.8]
    wz_pts = [H_total*0.25, H_total*0.55, H_total*0.8]
    wx_pts = [-scale*0.28]*3
    fig.add_trace(go.Cone(x=wx_pts, y=wy_pts, z=wz_pts,
                           u=[scale*0.28]*3, v=[0]*3, w=[0]*3,
                           colorscale=[[0,'#DC2626'],[1,'#DC2626']],
                           showscale=False, sizemode='absolute',
                           sizeref=scale*0.08, name='ลม'))

    # Pressure arrows on windward face (x=0 plane, simplified)
    for fd in floors_data:
        p_norm = fd['p_w_ext'] / max(abs(fd['p_w_ext']), 1)
        arr_z = fd['z_mid']
        arr_len = scale * 0.1 * min(abs(fd['p_w_ext'])/60, 1.5)
        fig.add_trace(go.Scatter3d(
            x=[-arr_len, 0], y=[L/2, L/2], z=[arr_z, arr_z],
            mode='lines', line=dict(color='#22C55E', width=4),
            showlegend=False))

    # Labels
    fig.add_trace(go.Scatter3d(
        x=[B/2, -B*0.12, -scale*0.3],
        y=[-scale*0.1, L/2, L*1.05],
        z=[0, 0, H_total/2],
        mode='text',
        text=[f'B={B}m (ขนานลม)', f'L={L}m (ตั้งฉากลม)', '🌬️ ทิศลม'],
        textfont=dict(color=['#2563EB','#D97706','#DC2626'], size=12),
        showlegend=False))

    fig.update_layout(
        scene=dict(
            xaxis_title='X (แนวลม)', yaxis_title='Y (ตั้งฉากลม)', zaxis_title='Z (ความสูง ม.)',
            aspectmode='data',
            camera=dict(eye=dict(x=-1.6, y=-1.4, z=1.1)),
            bgcolor='rgba(248,250,255,0.4)',
        ),
        margin=dict(l=0,r=0,b=0,t=36),
        title=dict(text='<b>แบบจำลอง 3 มิติ — มิติอาคารและทิศลม</b>', font=dict(size=14)),
        height=460,
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', y=-0.05),
    )
    return fig


def make_cross_section(mode='External', unit='kgf/m²'):
    fig = go.Figure()
    # Building outline
    if "แบน" in roof_type:
        ox = [0, B, B, 0, 0]; oy = [0, 0, H_total, H_total, 0]
    else:
        ox = [0, B, B, B/2, 0, 0]
        oy = [0, 0, H_total, H_total+h_ridge, H_total, 0]
    fig.add_trace(go.Scatter(x=ox, y=oy, fill='toself',
                              fillcolor='rgba(30,58,138,0.06)',
                              line=dict(color='#1E3A8A', width=2.5), showlegend=False))

    use_kN = 'kN' in unit
    ulbl = 'kN' if use_kN else 'kgf/m²'

    def arrow(x0,y0,x1,y1,val,col,anc='right'):
        fig.add_annotation(x=x1,y=y1,ax=x0,ay=y0,xref='x',yref='y',axref='x',ayref='y',
                           text=f'<b>{val:+.1f} {ulbl}</b>',
                           showarrow=True,arrowhead=2,arrowsize=1.3,
                           arrowcolor=col,font=dict(color=col,size=11),xanchor=anc)

    for fd in floors_data:
        fig.add_shape(type='line',x0=0,y0=fd['z_top'],x1=B,y1=fd['z_top'],
                      line=dict(color='#CBD5E1',width=1.2,dash='dot'))
        fig.add_annotation(x=B/2, y=fd['z_mid'], text=f"ชั้น {fd['floor']}",
                           showarrow=False, font=dict(size=10, color='#475569'))

        if use_kN:
            # Point load per floor
            if mode == 'External': fv = fd['F_net_ext']
            elif mode == 'Case 1': fv = fd['F_net_c1']
            else: fv = fd['F_net_c2']
            al = max(3.0, min(7.0, 2.5 + abs(fv)/50.0))
            arrow(-al, fd['z_top'], 0, fd['z_top'], fv, '#2563EB')
        else:
            # Distributed pressure
            if mode == 'External': pw = fd['p_w_ext']
            elif mode == 'Case 1': pw = fd['net_w_c1']
            else: pw = fd['net_w_c2']
            al = max(2.0, min(4.5, 1.5 + abs(pw)/40.0))
            col = '#16A34A' if pw >= 0 else '#DC2626'
            if pw >= 0: arrow(-al, fd['z_mid'], 0, fd['z_mid'], pw, col, 'right')
            else: arrow(0, fd['z_mid'], -al, fd['z_mid'], pw, col, 'left')

    if not use_kN:
        # Leeward
        if mode == 'External': pl = p_leeward_ext
        elif mode == 'Case 1': pl = net_l_c1
        else: pl = net_l_c2
        al = max(2.0, min(4.5, 1.5 + abs(pl)/40.0))
        col = '#EA580C'
        if pl >= 0: arrow(B+al, H_total/2, B, H_total/2, pl, col, 'left')
        else: arrow(B, H_total/2, B+al, H_total/2, pl, col, 'right')

        # Roof
        if "แบน" in roof_type:
            if mode == 'External': pr = p_roof_ext
            elif mode == 'Case 1': pr = net_roof_c1
            else: pr = net_roof_c2
            if pr >= 0: arrow(B/2, H_total+3, B/2, H_total, pr, '#DC2626', 'center')
            else: arrow(B/2, H_total, B/2, H_total+3, pr, '#7C3AED', 'center')
        else:
            if mode == 'External': prw, prl = p_roof_w_ext, p_roof_l_ext
            elif mode == 'Case 1': prw = p_roof_w_ext-p_int_neg; prl = p_roof_l_ext-p_int_neg
            else: prw = p_roof_w_ext-p_int_pos; prl = p_roof_l_ext-p_int_pos
            arrow(B/4, H_total+h_ridge/2+2.5, B/4, H_total+h_ridge/2, prw,
                  '#DC2626' if prw>=0 else '#7C3AED', 'center')
            arrow(3*B/4, H_total+h_ridge/2+2.5, 3*B/4, H_total+h_ridge/2, prl,
                  '#EA580C' if prl>=0 else '#7C3AED', 'center')
    else:
        if "จั่ว" in roof_type and abs(F_roof_horiz) > 0:
            al = max(3.0, min(7.0, 2.5 + abs(F_roof_horiz)/50.0))
            arrow(-al, H_total+h_ridge/2, 0, H_total+h_ridge/2, F_roof_horiz, '#2563EB')

    fig.update_layout(
        title=f'<b>แผนภาพหน้าตัด — {mode} ({ulbl})</b>',
        xaxis_title='ความกว้างขนานลม B (ม.)',
        yaxis_title='ความสูง z (ม.)',
        xaxis_range=[-12, B+12],
        yaxis_range=[-1, H_total+h_ridge+7],
        height=560,
        plot_bgcolor='white',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig

# ==========================================
# TABS
# ==========================================
tab1, tab2, tab3 = st.tabs([
    "🏗️ แบบจำลองและแผนภาพแรง",
    "⚖️ เปรียบเทียบแรงเฉือนฐาน",
    "📑 รายการคำนวณโดยละเอียด"
])

# ---- TAB 1: Visualizations ----
with tab1:
    # KPI cards
    k1, k2, k3, k4, k5 = st.columns(5)
    def kcard(col, label, val, unit=""):
        col.markdown(f"""
        <div class="metric-card">
          <div class="label">{label}</div>
          <div class="value">{val}</div>
          <div class="unit">{unit}</div>
        </div>""", unsafe_allow_html=True)

    kcard(k1, "V ลมออกแบบ",   f"{V_input:.0f}", "m/s")
    kcard(k2, "q พื้นฐาน",    f"{q:.2f}", "kgf/m²")
    kcard(k3, "Cg ที่ใช้",    f"{Cg_used:.3f}", "—")
    kcard(k4, "H อาคารรวม",   f"{H_total+h_ridge:.2f}", "ม.")
    kcard(k5, "V_wind ฐาน",   f"{V_wind:.1f}", "kN")

    st.markdown("---")
    st.plotly_chart(make_3d_figure(), use_container_width=True)
    st.markdown("---")

    col_ctrl1, col_ctrl2 = st.columns(2)
    view_mode = col_ctrl1.radio("กรณีโหลด (Load Case)",
                                 ["External", "Case 1", "Case 2"], horizontal=True)
    unit_mode = col_ctrl2.radio("หน่วยแสดงผล",
                                 ["kgf/m² (แรงกระจาย)", "kN (แรงสุทธิต่อชั้น)"], horizontal=True)
    st.plotly_chart(make_cross_section(view_mode, unit_mode), use_container_width=True)

    # Legend
    with st.expander("📌 คำอธิบายกรณีโหลด"):
        st.markdown("""
| กรณี | ความหมาย | ใช้เพื่อ |
|------|-----------|---------|
| **External** | แรงดันภายนอกเท่านั้น ไม่รวม GCpi | ตรวจสอบโครงสร้างหลัก |
| **Case 1** | +GCpi (แรงดันภายในบวก) | ออกแบบผนังและหลังคาด้านรับลม |
| **Case 2** | −GCpi (แรงดันภายในลบ) | ออกแบบผนังและหลังคาด้านตามลม / ยึดโยง |

> **หมายเหตุ:** สำหรับอาคารปิดทึบ แรง GCpi จะหักล้างกันเมื่อคำนวณแรงเฉือนสุทธิรวมทั้งตึก  
> (Net Base Shear จากทั้งสองกรณีจึงได้ค่าเท่ากัน) ความแตกต่างมีนัยสำหรับออกแบบชิ้นส่วน  
> อ้างอิง: มยผ. 1311-50 หมวด 3.5 และ ASCE 7 Section 27.3
        """)

# ---- TAB 2: Base Shear ----
with tab2:
    st.markdown('<div class="section-title">⚖️ เปรียบเทียบแรงเฉือนที่ฐานอาคาร (Base Shear)</div>',
                unsafe_allow_html=True)

    govern = V_wind > V_EQ_calc
    verdict_cls = "verdict-wind" if govern else "verdict-quake"
    verdict_txt = ("🌪️ แรงลมควบคุมการออกแบบ (Wind Governs)"
                   if govern else "🚨 แรงแผ่นดินไหวควบคุมการออกแบบ (Seismic Governs)")

    fig_bar = go.Figure()
    labels = ["V_Wind\n(แรงลม)", "V_EQ\n(แผ่นดินไหว)"]
    values = [V_wind, V_EQ_calc]
    colors = ["#3B82F6", "#EF4444"]
    fig_bar.add_trace(go.Bar(x=labels, y=values, marker_color=colors,
                              text=[f"{v:.1f} kN" for v in values],
                              textposition='auto',
                              textfont=dict(size=14, color='white'),
                              width=0.45))
    fig_bar.update_layout(height=380, plot_bgcolor='white',
                           yaxis_title='แรงเฉือนฐาน (kN)',
                           showlegend=False,
                           yaxis=dict(gridcolor='#F1F5F9'))

    bc1, bc2 = st.columns([3, 2])
    with bc1:
        st.plotly_chart(fig_bar, use_container_width=True)
    with bc2:
        st.markdown(f'<div class="{verdict_cls}"><b>{verdict_txt}</b></div>', unsafe_allow_html=True)
        st.markdown("---")
        ratio = V_wind / max(V_EQ_calc, 0.01)
        st.markdown(f"""
| พารามิเตอร์ | ค่า |
|-------------|-----|
| แรงลมสูงสุด V_Wind | **{V_wind:.2f} kN** |
| แรงแผ่นดินไหว V_EQ | **{V_EQ_calc:.2f} kN** |
| อัตราส่วน V_Wind / V_EQ | **{ratio:.3f}** |
| แรงที่ควบคุม (Governing) | **{max(V_wind, V_EQ_calc):.2f} kN** |
        """)

    # Storey shear diagram
    st.markdown('<div class="section-title">แรงเฉือนสะสมรายชั้น (Storey Shear Profile)</div>',
                unsafe_allow_html=True)
    storey_shears = []
    cum = 0
    for fd in reversed(floors_data):
        cum += fd['F_net_ext']
        storey_shears.insert(0, (fd['floor'], fd['z_top'], cum + (F_roof_horiz if fd['floor'] == num_stories else 0)))

    fig_ss = go.Figure()
    sh_vals = [s[2] for s in storey_shears] + [0]
    h_vals  = [s[1] for s in storey_shears] + [0]
    fig_ss.add_trace(go.Scatter(x=sh_vals, y=h_vals, mode='lines+markers',
                                 line=dict(color='#2563EB', width=3),
                                 marker=dict(size=8, color='#1D4ED8'),
                                 fill='tozerox', fillcolor='rgba(59,130,246,0.12)',
                                 name='แรงเฉือนสะสม'))
    fig_ss.update_layout(height=350, plot_bgcolor='white',
                          xaxis_title='แรงเฉือนสะสม (kN)',
                          yaxis_title='ระดับความสูง z (ม.)',
                          yaxis=dict(gridcolor='#F1F5F9'),
                          xaxis=dict(gridcolor='#F1F5F9'))
    st.plotly_chart(fig_ss, use_container_width=True)

# ---- TAB 3: Calculation Report ----
with tab3:
    st.markdown("""
    <div style="background:#0F2557;color:white;padding:18px 22px;border-radius:10px;margin-bottom:16px;">
      <h2 style="margin:0;font-size:1.3rem;font-weight:700;">📑 รายการคำนวณแรงลม — มยผ. 1311-50</h2>
      <p style="margin:4px 0 0 0;color:#93C5FD;font-size:0.88rem;">
        มาตรฐานการคำนวณแรงลมและการตอบสนองของอาคาร · กรมโยธาธิการและผังเมือง
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # หมวด 1: ข้อมูลโครงการและสมมุติฐาน
    # ──────────────────────────────────────────────
    st.markdown("## 1. ข้อมูลโครงการและข้อกำหนดการออกแบบ")
    i1, i2, i3 = st.columns(3)
    with i1:
        st.markdown(f"""
**ความเร็วลมอ้างอิง V**  
&emsp;V = **{V_input:.1f} m/s**  
&emsp;<span class="ref-badge">มยผ. ตารางที่ 4</span>

**สภาพภูมิประเทศ**  
&emsp;{EXPOSURE_PARAMS[exp_key]['label']}

**ตัวคูณภูมิประเทศ Ct**  
&emsp;Ct = **{Ct_input:.2f}**
""", unsafe_allow_html=True)
    with i2:
        st.markdown(f"""
**มิติอาคาร**  
&emsp;B = {B} ม. (ขนานลม, along-wind)  
&emsp;L = {L} ม. (ตั้งฉากลม, across-wind)  
&emsp;H = {H_total:.2f} ม. (ความสูงตึก)

**ประเภทหลังคา**  
&emsp;{roof_type}{"  (ความชัน " + str(roof_angle_deg) + "°, h_ridge = " + f"{h_ridge:.2f}" + " ม.)" if "จั่ว" in roof_type else ""}
""")
    with i3:
        st.markdown(f"""
**ค่าความสำคัญ Iw**  
&emsp;Iw = **{Iw_input:.2f}**

**GCpi (Internal Pressure)**  
&emsp;GCpi = **±{GCpi_val:.2f}** ({enclosure.split('(')[0].strip()})  
&emsp;<span class="ref-badge">มยผ. ตารางที่ 3</span>

**โหมด Gust Factor**  
&emsp;{"Flexible (Dynamic Cg)" if "Flexible" in gust_mode else "Rigid (Cg = 2.0)"}
""", unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # หมวด 2: แรงลมพื้นฐาน q
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 2. แรงลมปะทะอ้างอิงพื้นฐาน q  <span class='ref-badge'>มยผ. สมการ 3.1</span>", unsafe_allow_html=True)
    st.markdown(f"""
<div class="calc-block">
<div class="step-label">สูตร</div>

$$q = \\frac{{0.5 \\times \\rho_{{air}} \\times V^2}}{{g}} \\quad \\text{{[kgf/m²]}}$$

โดย: ρ_air = 1.25 kg/m³ (ความหนาแน่นอากาศมาตรฐาน), g = 9.80665 m/s²

<div class="step-label">แทนค่า</div>

$$q = \\frac{{0.5 \\times 1.25 \\times {V_input:.1f}^2}}{{9.80665}} = \\frac{{{0.5*1.25*V_input**2:.3f}}}{{9.80665}}$$

<div class="result-highlight">
✅ <b>q = {q:.4f} kgf/m² ≈ {q*9.80665:.2f} Pa</b>
</div>
</div>
""", unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # หมวด 3: Cg
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 3. สัมประสิทธิ์ลมกระโชก Cg  <span class='ref-badge'>มยผ. หมวด 4–5</span>",
                unsafe_allow_html=True)

    if dyn_det is None:
        st.markdown(f"""
<div class="calc-block">
<div class="step-label">อาคารแข็งเกร็ง (Rigid Structure, T₁ < 1 วินาที)</div>

ใช้ค่า Cg = 2.0 โดยตรงจากมาตรฐาน (Conservative approach)

<div class="result-highlight">✅ <b>Cg = 2.000</b> (ค่าคงที่สำหรับอาคารแข็งเกร็ง)</div>
</div>
""", unsafe_allow_html=True)
    else:
        d = dyn_det
        st.markdown(f"""
<div class="calc-block">
<div class="step-label">อาคารสูงเพรียว/พริ้วไหว (Flexible Structure)</div>

**ข้อมูลนำเข้า:** T₁ = {T1_input:.3f} วินาที, n₁ = 1/T₁ = **{d['n1']:.4f} Hz**, β = {damp_input:.3f}

**ความสูงอ้างอิงเฉลี่ย:**
$$\\bar{{z}} = \\max(0.6H,\\, 4.5\\text{{ ม.}}) = \\max({0.6*H_total:.2f},\\, 4.5) = {d['z_bar']:.3f}\\text{{ ม.}}$$
</div>
""", unsafe_allow_html=True)

        st.markdown("#### 3.1 ความเข้มปั่นป่วนอากาศ I(z̄)  <span class='ref-badge'>มยผ. สมการ 4.3</span>", unsafe_allow_html=True)
        st.markdown(f"""
<div class="calc-block">

$$I_{{\\bar{{z}}}} = c \\cdot \\left(\\frac{{10}}{{\\bar{{z}}}}\\right)^{{1/6}}$$

แทนค่า: c = {EXPOSURE_PARAMS[exp_key]['c']}, z̄ = {d['z_bar']:.3f} ม.

$$I_{{\\bar{{z}}}} = {EXPOSURE_PARAMS[exp_key]['c']} \\times \\left(\\frac{{10}}{{{d['z_bar']:.3f}}}\\right)^{{1/6}} = {EXPOSURE_PARAMS[exp_key]['c']} \\times {(10/d['z_bar'])**(1/6):.5f}$$

<div class="result-highlight">✅ <b>I(z̄) = {d['Iz_bar']:.5f}</b></div>
</div>
""", unsafe_allow_html=True)

        st.markdown("#### 3.2 สเกลความปั่นป่วน L(z̄)  <span class='ref-badge'>มยผ. สมการ 4.4</span>", unsafe_allow_html=True)
        st.markdown(f"""
<div class="calc-block">

$$L_{{\\bar{{z}}}} = \\ell \\cdot \\left(\\frac{{\\bar{{z}}}}{{10}}\\right)^\\epsilon$$

แทนค่า: ℓ = {EXPOSURE_PARAMS[exp_key]['ell']}, ε = {EXPOSURE_PARAMS[exp_key]['epsilon']}, z̄ = {d['z_bar']:.3f}

$$L_{{\\bar{{z}}}} = {EXPOSURE_PARAMS[exp_key]['ell']} \\times \\left(\\frac{{{d['z_bar']:.3f}}}{{10}}\\right)^{{{EXPOSURE_PARAMS[exp_key]['epsilon']}}} = {EXPOSURE_PARAMS[exp_key]['ell']} \\times {(d['z_bar']/10)**EXPOSURE_PARAMS[exp_key]['epsilon']:.5f}$$

<div class="result-highlight">✅ <b>L(z̄) = {d['Lz_bar']:.4f} ม.</b></div>
</div>
""", unsafe_allow_html=True)

        st.markdown("#### 3.3 ความเร็วลมเฉลี่ยที่ z̄  <span class='ref-badge'>มยผ. สมการ 4.6</span>", unsafe_allow_html=True)
        st.markdown(f"""
<div class="calc-block">

$$\\bar{{V}}_{{\\bar{{z}}}} = \\bar{{b}} \\cdot \\left(\\frac{{\\bar{{z}}}}{{10}}\\right)^{{\\bar{{\\alpha}}}} \\cdot V$$

แทนค่า: b̄ = {EXPOSURE_PARAMS[exp_key]['b_bar']}, ᾱ = {EXPOSURE_PARAMS[exp_key]['alpha_bar']}, V = {V_input}

$$\\bar{{V}} = {EXPOSURE_PARAMS[exp_key]['b_bar']} \\times \\left(\\frac{{{d['z_bar']:.3f}}}{{10}}\\right)^{{{EXPOSURE_PARAMS[exp_key]['alpha_bar']}}} \\times {V_input} = {d['V_bar_z']:.4f}\\text{{ m/s}}$$

<div class="result-highlight">✅ <b>V̄(z̄) = {d['V_bar_z']:.4f} m/s</b></div>
</div>
""", unsafe_allow_html=True)

        st.markdown("#### 3.4 ตัวประกอบพื้นหลัง Q  <span class='ref-badge'>มยผ. สมการ 4.5</span>", unsafe_allow_html=True)
        st.markdown(f"""
<div class="calc-block">

$$Q = \\sqrt{{\\frac{{1}}{{1 + 0.63 \\left(\\frac{{L_{{dim}} + H}}{{L_{{\\bar{{z}}}}}}\\right)^{{0.63}}}}}}$$

(L_dim = {L} ม. = มิติตั้งฉากลม ซึ่งคือความกว้างผิวรับลม)

$$Q = \\sqrt{{\\frac{{1}}{{1 + 0.63 \\times \\left(\\frac{{{L}+{H_total:.2f}}}{{{d['Lz_bar']:.4f}}}\\right)^{{0.63}}}}}} = \\sqrt{{\\frac{{1}}{{1 + 0.63 \\times {((L+H_total)/d['Lz_bar'])**0.63:.5f}}}}}$$

<div class="result-highlight">✅ <b>Q = {d['Q']:.5f}</b> (Background turbulence factor)</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("#### 3.5 สเปกตรัมลมและการสั่นพ้อง (Rn, Rh, RB, RL, R)  <span class='ref-badge'>มยผ. สมการ 4.7–4.11</span>", unsafe_allow_html=True)
        st.markdown(f"""
<div class="calc-block">

**ความถี่ไร้มิติ N₁:**
$$N_1 = \\frac{{n_1 \\cdot L_{{\\bar{{z}}}}}}{{\\bar{{V}}}} = \\frac{{{d['n1']:.4f} \\times {d['Lz_bar']:.4f}}}{{{d['V_bar_z']:.4f}}} = {d['N1']:.5f}$$

**สเปกตรัมกำลังลม Rn:**
$$R_n = \\frac{{7.47 N_1}}{{(1 + 10.3 N_1)^{{5/3}}}} = \\frac{{7.47 \\times {d['N1']:.5f}}}{{(1 + 10.3 \\times {d['N1']:.5f})^{{5/3}}}} = {d['Rn']:.5f}$$

**ตัวประกอบขนาด η และ R (Size Reduction Factors):**

| พารามิเตอร์ | สูตร | ค่า η | R |
|-------------|------|-------|---|
| ความสูง (h) | η_h = 4.6·n₁·H/V̄ | {d['eta_h']:.4f} | Rh = {d['Rh']:.5f} |
| ตั้งฉากลม (L) | η_B = 4.6·n₁·L/V̄ | {d['eta_B']:.4f} | RB = {d['RB']:.5f} |
| ขนานลม (B) | η_L = 15.4·n₁·B/V̄ | {d['eta_L']:.4f} | RL = {d['RL']:.5f} |

สูตร R_size(η) = (1/η) − [1/(2η²)]·(1 − e^(−2η))

**ตัวประกอบการสั่นพ้องรวม R:**
$$R = \\sqrt{{\\frac{{1}}{{\\beta}} \\cdot R_n \\cdot R_h \\cdot R_B \\cdot (0.53 + 0.47 R_L)}}$$
$$R = \\sqrt{{\\frac{{1}}{{{damp_input:.3f}}} \\times {d['Rn']:.5f} \\times {d['Rh']:.5f} \\times {d['RB']:.5f} \\times (0.53 + 0.47 \\times {d['RL']:.5f})}}$$

<div class="result-highlight">✅ <b>R = {d['R']:.5f}</b> (Resonant response factor)</div>
</div>
""", unsafe_allow_html=True)

        gq = d['g_q']; gr = d['g_r']
        log_t = math.log(3600*d['n1'])
        st.markdown("#### 3.6 Peak Factors และ Cg สุดท้าย  <span class='ref-badge'>มยผ. สมการ 4.1, 4.12</span>", unsafe_allow_html=True)
        st.markdown(f"""
<div class="calc-block">

**Peak Factor g_q (Background):** g_q = **{gq:.2f}** (ค่าคงที่ตามมาตรฐาน)

**Peak Factor g_r (Resonant):**
$$g_r = \\sqrt{{2 \\ln(3600 n_1)}} + \\frac{{0.577}}{{\\sqrt{{2 \\ln(3600 n_1)}}}}$$
$$g_r = \\sqrt{{2 \\times {log_t:.4f}}} + \\frac{{0.577}}{{\\sqrt{{2 \\times {log_t:.4f}}}}} = {gr:.4f}$$

**Cg แบบพลศาสตร์:**
$$C_g = 1 + 2 \\cdot I_{{\\bar{{z}}}} \\cdot \\sqrt{{(g_q \\cdot Q)^2 + (g_r \\cdot R)^2}}$$
$$C_g = 1 + 2 \\times {d['Iz_bar']:.5f} \\times \\sqrt{{({gq} \\times {d['Q']:.5f})^2 + ({gr:.4f} \\times {d['R']:.5f})^2}}$$
$$C_g = 1 + 2 \\times {d['Iz_bar']:.5f} \\times {math.sqrt((gq*d['Q'])**2+(gr*d['R'])**2):.5f} = {d['Cg_dyn']:.5f}$$

บังคับ: Cg ≥ 1.5 ตามมาตรฐาน

<div class="result-highlight">
✅ <b>Cg = max({d['Cg_dyn']:.4f}, 1.5) = {Cg_used:.4f}</b>
</div>
</div>
""", unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # หมวด 4: Ce และ qz รายชั้น
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 4. สัมประสิทธิ์ความสูงและแรงดันอ้างอิงรายชั้น (Ce และ qz)  <span class='ref-badge'>มยผ. สมการ 3.2, ตารางที่ 1</span>", unsafe_allow_html=True)

    p_exp = EXPOSURE_PARAMS[exp_key]
    st.markdown(f"""
<div class="calc-block">
<div class="step-label">สูตร Ce</div>

$$C_e(z) = \\left(\\frac{{z_{{eff}}}}{{10}}\\right)^{{{p_exp['alpha']}}} \\quad \\text{{อยู่ในช่วง [{p_exp['ce_min']}, {p_exp['ce_max']}]}}$$

โดย z_eff = max(z, 6.0 ม.) — ใช้ความสูงอ้างอิงต่ำสุด 6.0 ม. ตามมาตรฐาน

**แรงดันลมอ้างอิงที่ความสูง z:**  q_z = q × Ce(z) × Ct = {q:.4f} × Ce × {Ct_input:.2f}

**แรงดันท้ายลม** (ใช้ Ce ที่ระดับ H คงที่): q_h = {qh:.4f} kgf/m²  
&emsp;Ce(H={H_total:.2f} ม.) = ({z_eff_H:.2f}/10)^{p_exp['alpha']} = {raw_Ce_H:.5f} → ควบคุมที่ **{Ce_H:.5f}**
</div>
""", unsafe_allow_html=True)

    # ตารางสรุปรายชั้น
    rows = []
    for fd in floors_data:
        rows.append({
            "ชั้น": fd['floor'],
            "z_mid (ม.)": f"{fd['z_mid']:.2f}",
            "z_eff (ม.)": f"{fd['z_eff_m']:.2f}",
            "Ce": f"{fd['Ce_m']:.5f}",
            "q_z (kgf/m²)": f"{fd['q_z']:.4f}",
            "A_front (m²)": f"{fd['A_front']:.2f}",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # ──────────────────────────────────────────────
    # หมวด 5: แรงดันรายชั้นแบบละเอียด
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 5. แรงดันลมและแรงลัพธ์รายชั้น (Wind Pressure & Storey Force)  <span class='ref-badge'>มยผ. สมการ 3.3–3.5</span>", unsafe_allow_html=True)

    st.markdown(f"""
<div class="calc-block">
<div class="step-label">สูตรแรงดันลม (General)</div>

**ด้านรับลม (Windward)** — แปรผันตามความสูง:
$$p_{{w}}(z) = I_w \\cdot q_z \\cdot C_g \\cdot C_{{p,w}} \\quad \\text{{[kgf/m²]}}$$

**ด้านตามลม (Leeward)** — คงที่ที่ระดับยอด H:
$$p_l = I_w \\cdot q_H \\cdot C_g \\cdot C_{{p,l}} \\quad \\text{{[kgf/m²]}}$$

**แรงดันภายใน (Internal Pressure):**
$$p_{{int}} = \\pm GC_{{pi}} \\cdot q_H = \\pm {GCpi_val:.2f} \\times {qh:.4f} = \\pm {GCpi_val*qh:.4f}\\text{{kgf/m²}}$$

**แรงลัพธ์แนวราบต่อชั้น (kN):**
$$F_{{net}} = (p_w - p_l) \\times A_{{front}} \\times 0.00980665$$
$$\\text{{เมื่อ }} A_{{front}} = L \\times h = {L} \\times h_{{ชั้น}}$$

<span class="formula-note">หมายเหตุ: ตัวแปลงหน่วย kgf/m² → kN: × 0.00980665 (= 9.80665 N/kgf × 10⁻³ kN/N)</span>
</div>
""", unsafe_allow_html=True)

    # แสดงรายชั้น
    for fd in floors_data:
        pw_sub = f"{Iw_input:.2f} × {fd['q_z']:.4f} × {Cg_used:.4f} × {Cp_w:.2f}"
        pl_sub = f"{Iw_input:.2f} × {qh:.4f} × {Cg_used:.4f} × ({Cp_l:.2f})"
        with st.expander(f"📐 ชั้น {fd['floor']}  |  z = {fd['z_bot']:.2f} – {fd['z_top']:.2f} ม.  |  F_net = {fd['F_net_ext']:.3f} kN"):
            st.markdown(f"""
<div class="floor-card">
<h4>ชั้น {fd['floor']} — ข้อมูลรับแรงลม</h4>

| พารามิเตอร์ | ค่า |
|-------------|-----|
| z_mid (ความสูงกึ่งกลางชั้น) | **{fd['z_mid']:.3f} ม.** |
| z_eff = max(z_mid, 6.0) | **{fd['z_eff_m']:.3f} ม.** |
| Ce(z_mid) = ({fd['z_eff_m']:.3f}/10)^{p_exp['alpha']} | raw = {fd['raw_Ce_m']:.5f} → **{fd['Ce_m']:.5f}** |
| q_z = {q:.4f} × {fd['Ce_m']:.5f} × {Ct_input:.2f} | **{fd['q_z']:.4f} kgf/m²** |
| พื้นที่รับลม A = L × h = {L} × {fd['h']:.1f} | **{fd['A_front']:.2f} m²** |
</div>
""", unsafe_allow_html=True)

            # Windward
            st.markdown("**แรงดันด้านรับลม (Windward):**")
            st.latex(f"p_{{w}} = I_w \\cdot q_z \\cdot C_g \\cdot C_{{p,w}} = {pw_sub} = {fd['p_w_ext']:.4f}\\text{{kgf/m²}}")
            st.markdown(f"**แรง F_w = {fd['p_w_ext']:.4f} × {fd['A_front']:.2f} × 0.00980665 = {fd['F_w_ext']:.4f} kN**")

            # Leeward
            st.markdown("**แรงดันด้านตามลม (Leeward — คงที่ที่ระดับ H):**")
            st.latex(f"p_l = I_w \\cdot q_H \\cdot C_g \\cdot C_{{p,l}} = {pl_sub} = {p_leeward_ext:.4f}\\text{{kgf/m²}}")
            st.markdown(f"**แรง F_l = {p_leeward_ext:.4f} × {fd['A_front']:.2f} × 0.00980665 = {fd['F_l_ext']:.4f} kN**")

            # Net
            st.markdown("**แรงสุทธิแนวราบของชั้น:**")
            st.latex(f"F_{{net}} = F_w - F_l = {fd['F_w_ext']:.4f} - ({fd['F_l_ext']:.4f}) = {fd['F_net_ext']:.4f}\\text{{ kN}}")

            # Case 1 & 2 pressures
            st.markdown("**กรณีรวมแรงดันภายใน:**")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown(f"""
**Case 1: +GCpi (แรงดันภายในบวก)**  
p_w,net = {fd['net_w_c1']:.4f} kgf/m²  
p_l,net = {net_l_c1:.4f} kgf/m²  
F_w = {fd['F_w_c1']:.3f} kN, F_l = {fd['F_l_c1']:.3f} kN  
F_net_c1 = {fd['F_net_c1']:.3f} kN
""")
            with col_c2:
                st.markdown(f"""
**Case 2: −GCpi (แรงดันภายในลบ)**  
p_w,net = {fd['net_w_c2']:.4f} kgf/m²  
p_l,net = {net_l_c2:.4f} kgf/m²  
F_w = {fd['F_w_c2']:.3f} kN, F_l = {fd['F_l_c2']:.3f} kN  
F_net_c2 = {fd['F_net_c2']:.3f} kN
""")

    # ──────────────────────────────────────────────
    # หมวด 6: หลังคา
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 6. แรงดันหลังคา (Roof Pressure)  <span class='ref-badge'>มยผ. หมวด 3.6</span>", unsafe_allow_html=True)

    if "แบน" in roof_type:
        net_r_c1 = p_roof_ext - p_int_neg
        net_r_c2 = p_roof_ext - p_int_pos
        st.markdown(f"""
<div class="calc-block">

**แรงดันหลังคาแบน (Flat Roof):**

$$p_{{roof,ext}} = I_w \\cdot q_H \\cdot C_g \\cdot C_{{p,r}} = {Iw_input:.2f} \\times {qh:.4f} \\times {Cg_used:.4f} \\times ({Cp_r:.2f}) = {p_roof_ext:.4f}\\text{{kgf/m²}}$$

**รวมแรงดันภายใน:**

| กรณี | แรงดันสุทธิ |
|------|------------|
| External Only | p = {p_roof_ext:.4f} kgf/m² |
| Case 1 (+GCpi) | p = {p_roof_ext:.4f} − ({p_int_neg:.4f}) = **{net_r_c1:.4f}** kgf/m² |
| Case 2 (−GCpi) | p = {p_roof_ext:.4f} − ({p_int_pos:.4f}) = **{net_r_c2:.4f}** kgf/m² |

พื้นที่หลังคา = B × L = {B} × {L} = {B*L:.1f} m² (แรงนี้เป็นแรงดิ่ง — uplift)

<span class="formula-note">หมายเหตุ: หลังคาแบนไม่มีแรงแนวราบสุทธิ (F_roof_horiz = 0) ส่งผลต่อโมเมนต์พลิกคว่ำเท่านั้น</span>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div class="calc-block">

**หลังคาจั่ว (Gable Roof) — ความชัน {roof_angle_deg:.1f}°**

$$h_{{ridge}} = \\frac{{B}}{{2}} \\cdot \\tan({roof_angle_deg:.1f}°) = \\frac{{{B}}}{{2}} \\times {math.tan(math.radians(roof_angle_deg)):.5f} = {h_ridge:.4f}\\text{{ ม.}}$$

**แรงดันหลังคาฝั่งรับลม:**
$$p_{{r,w}} = I_w \\cdot q_H \\cdot C_g \\cdot C_{{p,r,w}} = {Iw_input:.2f} \\times {qh:.4f} \\times {Cg_used:.4f} \\times ({Cp_r_w:.2f}) = {p_roof_w_ext:.4f}\\text{{kgf/m²}}$$

**แรงดันหลังคาฝั่งตามลม:**
$$p_{{r,l}} = I_w \\cdot q_H \\cdot C_g \\cdot C_{{p,r,l}} = {Iw_input:.2f} \\times {qh:.4f} \\times {Cg_used:.4f} \\times ({Cp_r_l:.2f}) = {p_roof_l_ext:.4f}\\text{{kgf/m²}}$$

**แรงเฉือนแนวราบจากหลังคาจั่ว** (ฉายบนพื้นที่แนวตั้งของหน้าจั่ว):
$$A_{{roof,vert}} = h_{{ridge}} \\times L = {h_ridge:.4f} \\times {L} = {h_ridge*L:.4f}\\text{{ m}}^2$$
$$F_{{roof,horiz}} = (p_{{r,w}} - p_{{r,l}}) \\times A_{{roof,vert}} \\times 0.00980665$$
$$F_{{roof,horiz}} = ({p_roof_w_ext:.4f} - {p_roof_l_ext:.4f}) \\times {h_ridge*L:.4f} \\times 0.00980665$$
$$= {p_roof_w_ext - p_roof_l_ext:.4f} \\times {h_ridge*L:.4f} \\times 0.00980665$$

<div class="result-highlight">✅ <b>F_roof_horiz = {F_roof_horiz:.4f} kN</b> (แรงแนวราบที่หัวเสาอาคาร)</div>
</div>
""", unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # หมวด 7: สรุปแรงเฉือนฐาน
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 7. สรุปแรงเฉือนที่ฐานอาคาร (Total Base Shear)", unsafe_allow_html=True)

    sum_floors = sum(fd['F_net_ext'] for fd in floors_data)
    parts = [f"{fd['F_net_ext']:.3f}" for fd in floors_data]
    if "จั่ว" in roof_type:
        parts.append(f"{F_roof_horiz:.3f} (หลังคาจั่ว)")

    st.markdown(f"""
<div class="calc-block">
<div class="step-label">สมการรวมแรง</div>

$$V_{{wind}} = \\sum_{{i=1}}^{{n}} F_{{net,i}} + F_{{roof,horiz}}$$

**แรงแต่ละชั้น:**
| ชั้น | z_top (ม.) | F_w (kN) | F_l (kN) | F_net (kN) |
|------|-----------|---------|---------|----------|
""")
    for fd in floors_data:
        st.markdown(f"| {fd['floor']} | {fd['z_top']:.2f} | {fd['F_w_ext']:.3f} | {fd['F_l_ext']:.3f} | **{fd['F_net_ext']:.3f}** |")
    if "จั่ว" in roof_type:
        st.markdown(f"| หลังคาจั่ว | — | — | — | **{F_roof_horiz:.3f}** |")

    eq_parts = " + ".join(parts)
    st.markdown(f"""

**รวม:**
$$V_{{wind}} = {eq_parts} = {V_wind:.4f}\\text{{ kN}}$$

<div class="result-highlight" style="font-size:1.1rem;">
🎯 <b>V_wind (Base Shear รวม) = {V_wind:.4f} kN</b>
</div>
</div>
""", unsafe_allow_html=True)

    # ──────────────────────────────────────────────
    # หมวด 8: ตารางสรุปรวม
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 8. ตารางสรุปแรงดันและแรงสุทธิ (Summary Table)", unsafe_allow_html=True)

    rows_full = []
    for fd in floors_data:
        rows_full.append({
            "ชั้น": fd['floor'],
            "z_bot–z_top (ม.)": f"{fd['z_bot']:.2f}–{fd['z_top']:.2f}",
            "Ce": f"{fd['Ce_m']:.5f}",
            "q_z (kgf/m²)": f"{fd['q_z']:.4f}",
            "p_w Ext (kgf/m²)": f"{fd['p_w_ext']:.4f}",
            "p_l Ext (kgf/m²)": f"{p_leeward_ext:.4f}",
            "A_front (m²)": f"{fd['A_front']:.2f}",
            "F_w (kN)": f"{fd['F_w_ext']:.4f}",
            "F_l (kN)": f"{fd['F_l_ext']:.4f}",
            "F_net (kN)": f"{fd['F_net_ext']:.4f}",
        })
    df_full = pd.DataFrame(rows_full)
    st.dataframe(df_full, use_container_width=True, hide_index=True)

    # ──────────────────────────────────────────────
    # หมวด 9: EQ
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 9. แรงแผ่นดินไหว V_EQ (Base Shear Comparison)")
    if "ประมาณ" in eq_mode:
        W_total_show = B * L * H_total * w_per_m2 * 0.00980665
        st.markdown(f"""
<div class="calc-block">
<div class="step-label">Equivalent Static Method (ประมาณการ)</div>

**น้ำหนักอาคารรวม W:**
$$W = B \\times L \\times H \\times w = {B} \\times {L} \\times {H_total:.2f} \\times {w_per_m2:.1f} \\times 0.00980665 = {W_total_show:.2f}\\text{{ kN}}$$

**แรงเฉือนฐานแผ่นดินไหว:**
$$V_{{EQ}} = C_s \\times W = {Cs_coeff:.3f} \\times {W_total_show:.2f} = {V_EQ_calc:.2f}\\text{{ kN}}$$

<span class="formula-note">หมายเหตุ: สูตรนี้เป็นการประมาณการเบื้องต้น ควรตรวจสอบตาม มยผ. 1302-52 อย่างเต็มรูปแบบ</span>
</div>
""", unsafe_allow_html=True)
    else:
        st.info(f"V_EQ ที่ระบุโดยตรง = **{V_EQ_calc:.2f} kN**")

    # ──────────────────────────────────────────────
    # สรุปท้าย
    # ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📌 สรุปผลการออกแบบ")
    govern2 = V_wind >= V_EQ_calc
    box_cls = "calc-block"
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(f"""
<div class="calc-block">

| รายการ | ค่า |
|--------|-----|
| q พื้นฐาน | **{q:.4f} kgf/m²** |
| Cg ที่ใช้ | **{Cg_used:.4f}** |
| Ce(H) | **{Ce_H:.5f}** |
| qh ที่ระดับยอด | **{qh:.4f} kgf/m²** |
| GCpi | **±{GCpi_val:.2f}** |
| F_roof_horiz | **{F_roof_horiz:.3f} kN** |
| **V_wind รวม** | **{V_wind:.3f} kN** |
| **V_EQ** | **{V_EQ_calc:.3f} kN** |
| **แรงควบคุม** | **{"WIND 🌪️" if govern2 else "SEISMIC 🚨"}** |
</div>
""", unsafe_allow_html=True)
    with col_s2:
        if govern2:
            st.success(f"🌪️ **แรงลมควบคุมการออกแบบ**\n\nV_wind = **{V_wind:.2f} kN** > V_EQ = {V_EQ_calc:.2f} kN\n\nออกแบบโครงสร้างด้วยแรงเฉือนฐาน **{V_wind:.2f} kN**")
        else:
            st.info(f"🚨 **แรงแผ่นดินไหวควบคุมการออกแบบ**\n\nV_EQ = **{V_EQ_calc:.2f} kN** > V_wind = {V_wind:.2f} kN\n\nออกแบบโครงสร้างด้วยแรงเฉือนฐาน **{V_EQ_calc:.2f} kN**")

        st.markdown(f"""
<div class="warning-box">
⚠️ <b>ข้อสังเกตสำคัญ:</b><br>
• Cp_w = {Cp_w:.2f}, Cp_l = {Cp_l:.2f} ควรตรวจสอบจาก มยผ. ตารางที่ 2 ตาม H/B และ L/B ratio<br>
• H/B = {H_total/B:.2f}, L/B = {L/B:.2f}<br>
• GCpi = ±{GCpi_val:.2f} ตรวจสอบลักษณะการปิดล้อมให้ถูกต้อง<br>
• แรงลมนี้คิดในทิศทางเดียว — ต้องตรวจสอบในทิศตั้งฉากด้วย
</div>
""", unsafe_allow_html=True)

    # References
    st.markdown("---")
    with st.expander("📚 อ้างอิงมาตรฐาน"):
        st.markdown("""
| รหัส | ชื่อมาตรฐาน |
|------|------------|
| มยผ. 1311-50 | มาตรฐานการคำนวณแรงลมและการตอบสนองของอาคาร · กรมโยธาธิการและผังเมือง 2550 |
| มยผ. 1302-52 | มาตรฐานการออกแบบอาคารต้านทานการสั่นสะเทือนของแผ่นดินไหว |
| NBCC 2010 | National Building Code of Canada — Dynamic Gust Factor Method |
| ASCE 7-22 | Minimum Design Loads and Associated Criteria for Buildings — Ch. 26–27 |
        """)
