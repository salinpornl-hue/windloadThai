import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# ==========================================
# ฐานข้อมูลและฟังก์ชันคณิตศาสตร์ (มยผ. 1311-50 / 1302)
# ==========================================
PROVINCE_V = {
    "กรุงเทพฯ / นนทบุรี / ปทุมธานี / สมุทรปราการ / สมุทรสาคร (25 m/s)": 25.0,
    "ชลบุรี / ระยอง / จันทบุรี / ตราด (30 m/s)": 30.0,
    "ภูเก็ต / พังงา / กระบี่ (27 m/s)": 27.0,
    "เชียงใหม่ / เชียงราย / พิษณุโลก / แม่ฮ่องสอน (25 m/s)": 25.0,
    "นครราชสีมา / ขอนแก่น / อุดรธานี / อุบลราชธานี (25 m/s)": 25.0,
    "สงขลา / สุราษฎร์ธานี / นครศรีธรรมราช (25 m/s)": 25.0,
    "🛠️ กำหนดค่าความเร็วลมเอง (Manual Input)": 25.0
}

def calculate_q(V):
    return (0.5 * 1.25 * (V ** 2)) / 9.80665

def get_Ce_details(z, exposure):
    z_eff = max(z, 6.0) 
    if 'A' in exposure: alpha, min_val, max_val = 0.20, 0.9, 1.5
    elif 'B' in exposure: alpha, min_val, max_val = 0.28, 0.7, 1.2
    else: alpha, min_val, max_val = 0.40, 0.5, 1.0
    
    raw_ce = (z_eff / 10.0) ** alpha
    ce = min(max(raw_ce, min_val), max_val)
    exp = f"ใช้สูตร: ({z_eff}/10)^{alpha} = {raw_ce:.4f} → ควบคุมที่ {ce:.3f}"
    if z < 6.0: exp = f"ความสูง {z}ม. < 6.0ม. ให้คิดที่ 6.0ม. | " + exp
    return ce, exp

# ฟังก์ชันคำนวณค่า Gust Effect Factor (Cg) แบบพลศาสตร์ตาม มยผ. 1311-50 / ASCE 7
def calculate_dynamic_cg(H, B, L, T1, damping, exposure, V):
    n1 = 1.0 / T1 if T1 > 0 else 1.0
    z_bar = max(0.6 * H, 4.5) # ความสูงประสิทธิผล
    
    # กำหนดพารามิเตอร์ตามสภาพภูมิประเทศ (Terrain Parameters)
    if 'A' in exposure:
        c, ell, epsilon, alpha_bar, b_bar = 0.30, 98.0, 0.33, 0.15, 0.65
    elif 'B' in exposure:
        c, ell, epsilon, alpha_bar, b_bar = 0.20, 152.0, 0.25, 0.25, 0.45
    else: # С
        c, ell, epsilon, alpha_bar, b_bar = 0.15, 198.0, 0.20, 0.35, 0.30
        
    # 1. ความเข้มข้นของลมแปรปรวน (Turbulence Intensity)
    Iz_bar = c * ((10.0 / z_bar) ** (1.0 / 6.0))
    
    # 2. มาตราส่วนความยาวของลมแปรปรวน (Integral Length Scale)
    Lz_bar = ell * ((z_bar / 10.0) ** epsilon)
    
    # 3. Background Response (Q)
    Q = math.sqrt(1.0 / (1.0 + 0.63 * (((B + H) / Lz_bar) ** 0.63)))
    
    # 4. Resonant Response (R)
    # ความเร็วลมเฉลี่ยรายชั่วโมง ณ ความสูง z_bar
    V_bar_z = b_bar * ((z_bar / 10.0) ** alpha_bar) * V
    
    N1 = (n1 * Lz_bar) / V_bar_z if V_bar_z > 0 else 0.1
    Rn = (7.47 * N1) / ((1.0 + 10.3 * N1) ** (5.0 / 3.0))
    
    eta_h = (4.6 * n1 * H) / V_bar_z if V_bar_z > 0 else 0.1
    eta_B = (4.6 * n1 * B) / V_bar_z if V_bar_z > 0 else 0.1
    eta_L = (15.4 * n1 * L) / V_bar_z if V_bar_z > 0 else 0.1
    
    def get_R_size(eta):
        if eta <= 0: return 1.0
        return (1.0 / eta) - (1.0 / (2.0 * (eta**2))) * (1.0 - math.exp(-2.0 * eta))
        
    Rh = get_R_size(eta_h)
    RB = get_R_size(eta_B)
    RL = get_R_size(eta_L)
    
    R = math.sqrt((1.0 / damping) * Rn * Rh * RB * (0.53 + 0.47 * RL))
    
    # คำนวณค่ารวม Gust Factor (สเกลให้สอดคล้องกับพิกัดระบบ มยผ. ตัวคูณปกติฐานคือ 2.0)
    # สูตรพลศาสตร์สากล: g_q = 3.4, g_v = 3.4, g_r = sqrt(2*ln(3600*n1)) + 0.577/sqrt(2*ln(3600*n1))
    g_q, g_v = 3.4, 3.4
    term_ln = math.log(3600.0 * n1)
    g_r = math.sqrt(2.0 * term_ln) + 0.577 / math.sqrt(2.0 * term_ln)
    
    # หาค่าตัวคูณลมกระโชกพลศาสตร์สุทธิ
    Cg_dynamic = 1.0 + 2.0 * max(g_q * Iz_bar * Q, math.sqrt((g_q*Iz_bar*Q)**2 + (g_r*Iz_bar*R)**2))
    # คุมโครงสร้างไม่ให้ต่ำกว่าค่าเกณฑ์พื้นฐาน
    Cg_final = max(Cg_dynamic, 1.5)
    
    return Cg_final, {"Iz_bar": Iz_bar, "Lz_bar": Lz_bar, "Q": Q, "R": R, "N1": N1, "Rn": Rn, "V_bar_z": V_bar_z}

# ==========================================
# Streamlit UI Setup & Custom CSS
# ==========================================
st.set_page_config(page_title="Wind & Seismic Load Analyzer Pro V3.0", layout="wide")

st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .sub-title { font-size: 1.1rem; color: #4B5563; margin-bottom: 20px; }
    .section-header { font-size: 1.3rem; font-weight: 700; color: #1E3A8A; margin-top: 15px; margin-bottom: 10px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; }
    .card-stat { background-color: #F8FAFC; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0; text-align: center; }
    .verdict-box { padding: 15px; border-radius: 8px; font-size: 1.1rem; font-weight: bold; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌪️ Wind & Seismic Load Analyzer Pro V3.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบวิเคราะห์แรงลมสุทธิพลศาสตร์ (Dynamic Gust Factor) และเปรียบเทียบแรงเฉือนฐานอาคารตาม มยผ. 1311-50</div>', unsafe_allow_html=True)

# ==========================================
# SIDEBAR CONTROL PANEL
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/wind.png", width=60)
st.sidebar.markdown("### ⚙️ ข้อกำหนดการออกแบบ")

st.sidebar.subheader("1. พารามิเตอร์แรงลมและภูมิประเทศ")
prov_choice = st.sidebar.selectbox("ความเร็วลมพื้นที่", list(PROVINCE_V.keys()))
if "Manual" in prov_choice: V_input = st.sidebar.number_input("ความเร็วลม V (m/s)", value=25.0, step=1.0)
else: V_input = PROVINCE_V[prov_choice]
exposure = st.sidebar.selectbox("สภาพภูมิประเทศ", ['A (โล่ง/ชายฝั่ง)', 'B (ชานเมือง/ต้นไม้เยอะ)', 'C (ในเมือง/ตึกสูง)'], index=1)
Ct_input = st.sidebar.number_input("ตัวคูณภูมิประเทศ Ct (เนินเขา/หน้าผา)", value=1.00, step=0.01)
Iw_input = st.sidebar.selectbox("ค่าความสำคัญ (Iw)", [1.0, 1.15], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🌪️ 2. การวิเคราะห์ลมกระโชก (Gust Effect)")
gust_mode = st.sidebar.radio("ประเภทการตอบสนองโครงสร้าง:", ["อาคารแข็งเกร็งทั่วไป (Rigid: Cg = 2.0)", "อาคารสูงเพรียว/พริ้วไหว (Flexible: คำนวณพลศาสตร์)"])

if "Flexible" in gust_mode:
    T1_input = st.sidebar.number_input("คาบการสั่นธรรมชาติขั้นพื้นฐาน T1 (วินาที)", value=1.20, min_value=0.1, step=0.05, help="หาก T1 > 1.0 วินาที มยผ. บังคับคำนวณพลศาสตร์")
    damping_input = st.sidebar.number_input("อัตราส่วนความหน่วง (Damping Ratio)", value=0.020, min_value=0.005, max_value=0.05, step=0.005, format="%.3f", help="โครงสร้างคอนกรีตเสริมเหล็กปกติใช้ 0.02, โครงสร้างเหล็กใช้ 0.01")
else:
    Cg_input = 2.0

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 3. แรงแผ่นดินไหว (Base Shear)")
eq_mode = st.sidebar.radio("ที่มาของแผ่นดินไหว (V_EQ):", ["โปรแกรมประมาณการ (Equivalent Static)", "ระบุแรงเฉือนฐานเอง (kN)"])
if "ประมาณการ" in eq_mode:
    w_dl_ll = st.sidebar.number_input("น้ำหนักตึกเฉลี่ยรายชั้น (kgf/m²)", value=600.0, step=50.0)
    cs_coeff = st.sidebar.number_input("สัมประสิทธิ์แผ่นดินไหว Cs", value=0.050, step=0.005, format="%.3f")
else:
    V_EQ_manual = st.sidebar.number_input("ระบุ V_EQ (kN)", value=120.0, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("4. สัมประสิทธิ์ผิวกระทำและหลังคา")
enclosure = st.sidebar.selectbox("ลักษณะการปิดล้อม", ["อาคารปิดทึบ (Enclosed)", "อาคารปิดล้อมบางส่วน (Partially)"])
Cp_w = st.sidebar.number_input("Cp ผนังด้านรับลม (Windward)", value=0.8, step=0.05)
Cp_l = st.sidebar.number_input("Cp ผนังด้านตามลม (Leeward)", value=-0.5, step=0.05)

st.sidebar.markdown("**[ ข้อมูลหลังคาอาคาร ]**")
roof_type = st.sidebar.radio("ประเภทหลังคา:", ["แบน (Flat Roof)", "จั่ว / เพิงแหงน (Gable Roof)"])
if "แบน" in roof_type:
    Cp_r = st.sidebar.number_input("Cp หลังคาแบน (Roof Uplift)", value=-0.7, step=0.05)
    roof_angle = 0.0; h_roof = 0.0
else:
    roof_angle = st.sidebar.number_input("ความชันหลังคา (องศา)", value=15.0, step=1.0)
    Cp_r_w = st.sidebar.number_input("Cp หลังคาฝั่งรับลม (Windward)", value=-0.9, step=0.05)
    Cp_r_l = st.sidebar.number_input("Cp หลังคาฝั่งตามลม (Leeward)", value=-0.5, step=0.05)

GCpi = 0.55 if "Partially" in enclosure else 0.18

# ==========================================
# MAIN PAGE: Dimensions
# ==========================================
st.markdown('<div class="section-header">🏢 มิติรูปทรงและโครงสร้างระดับความสูงอาคาร</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1: B = st.number_input("ความกว้างอาคารขนานลม B (ม.)", value=15.0, min_value=1.0)
with c2: L = st.number_input("ความยาวอาคารตั้งฉากลม L (ม.)", value=20.0, min_value=1.0)
with c3: num_stories = st.number_input("จำนวนชั้นอาคารทั้งหมด", value=3, min_value=1)

with st.expander("📐 ปรับแต่งความสูงแยกรายชั้น (กรณีตึกแต่ละชั้นสูงไม่เท่ากัน)", expanded=True):
    floor_cols = st.columns(min(num_stories, 4))
    floor_heights = []
    for i in range(num_stories):
        with floor_cols[i % 4]:
            h_val = st.number_input(f"ชั้น {i+1} (ม.)", value=4.0 if i==0 else 3.5, min_value=1.0, key=f"h_{i}")
            floor_heights.append(h_val)
H_total = sum(floor_heights)

if "จั่ว" in roof_type:
    h_roof = (B / 2.0) * math.tan(math.radians(roof_angle))
else:
    h_roof = 0.0

# ==========================================
# ENGINE: ประมวลผลและคำนวณพลศาสตร์ Cg
# ==========================================
if "Flexible" in gust_mode:
    Cg_calculated, dyn_components = calculate_dynamic_cg(H_total, B, L, T1_input, damping_input, exposure, V_input)
    Cg_final_used = Cg_calculated
else:
    Cg_final_used = Cg_input
    dyn_components = None

q = calculate_q(V_input)
`Ce_H`, _ = get_Ce_details(H_total, exposure)
qh = q * `Ce_H` * Ct_input 

p_leeward = Iw_input * qh * Cg_final_used * Cp_l 
p_int_pos = qh * GCpi     
p_int_neg = qh * (-GCpi)  

net_l_c1, net_l_c2 = p_leeward - p_int_neg, p_leeward - p_int_pos

# --- คำนวณแรงลัพธ์หลังคา ---
if "แบน" in roof_type:
    p_roof = Iw_input * qh * Cg_final_used * Cp_r
    force_roof_horiz = 0.0
else:
    p_roof_w = Iw_input * qh * Cg_final_used * Cp_r_w
    p_roof_l = Iw_input * qh * Cg_final_used * Cp_r_l
    area_vert_roof = h_roof * L
    force_roof_horiz = (p_roof_w - p_roof_l) * area_vert_roof * 0.00980665

# --- คำนวณแรงรายชั้น ---
z_cum = 0
floors_data = []

for i in range(num_stories):
    h = floor_heights[i]
    z_bot, z_top = z_cum, z_cum + h
    z_mid = (z_bot + z_top) / 2.0
    
    Ce_mid, Ce_exp = get_Ce_details(z_mid, exposure)
    p_w = Iw_input * q * Ce_mid * Ct_input * Cg_final_used * Cp_w
    
    net_w_c1 = p_w - p_int_neg
    net_w_c2 = p_w - p_int_pos
    area_front = L * h  
    
    force_w_ext = p_w * area_front * 0.00980665
    force_w_c1 = net_w_c1 * area_front * 0.00980665
    force_w_c2 = net_w_c2 * area_front * 0.00980665
    
    force_l_ext = p_leeward * area_front * 0.00980665
    force_l_c1 = net_l_c1 * area_front * 0.00980665
    force_l_c2 = net_l_c2 * area_front * 0.00980665
    
    floors_data.append({
        "floor": i+1, "h": h, "z_bot": z_bot, "z_top": z_top, "z_mid": z_mid,
        "Ce": Ce_mid, "Ce_exp": Ce_exp, "p_w": p_w,
        "net_w_c1": net_w_c1, "net_w_c2": net_w_c2, "area_front": area_front,
        "force_w_ext": force_w_ext, "force_w_c1": force_w_c1, "force_w_c2": force_w_c2,
        "force_l_ext": force_l_ext, "force_l_c1": force_l_c1, "force_l_c2": force_l_c2,
        "force_c1": force_w_c1 - force_l_c1, "force_c2": force_w_c2 - force_l_c2
    })
    z_cum = z_top

V_wind_c1 = sum([f['force_c1'] for f in floors_data]) + force_roof_horiz
V_wind_c2 = sum([f['force_c2'] for f in floors_data]) + force_roof_horiz
V_wind_max = max(V_wind_c1, V_wind_c2)

if "ประมาณการ" in eq_mode:
    W_kN = (B * L) * num_stories * w_dl_ll * 0.00980665
    V_EQ_calc = cs_coeff * W_kN
else:
    V_EQ_calc = V_EQ_manual

# ==========================================
# PLOTLY PLOTTING
# ==========================================
def plot_cross_section(floors, mode, unit_display):
    fig = go.Figure()
    if "แบน" in roof_type:
        fig.add_trace(go.Scatter(x=[0, B, B, 0, 0], y=[0, 0, H_total, H_total, 0], fill="toself", fillcolor="rgba(30,58,138,0.05)", line=dict(color="#1E3A8A", width=3), showlegend=False))
    else:
        fig.add_trace(go.Scatter(x=[0, B, B, B/2, 0, 0], y=[0, 0, H_total, H_total+h_roof, H_total, 0], fill="toself", fillcolor="rgba(30,58,138,0.05)", line=dict(color="#1E3A8A", width=3), showlegend=False))
        
    is_kn = "kN" in unit_display
    unit_lbl = "kN" if is_kn else "kgf/m²"

    def draw_arrow(x_tail, y_tail, x_head, y_head, val, col, x_anc):
        fig.add_annotation(x=x_head, y=y_head, ax=x_tail, ay=y_tail, xref="x", yref="y", axref="x", ayref="y",
            text=f"<b>{val:.1f} {unit_lbl}</b>", showarrow=True, arrowhead=2, arrowsize=1.2, arrowcolor=col, font=dict(color=col, size=12), xanchor=x_anc)

    for f in floors:
        fig.add_shape(type="line", x0=0, y0=f['z_top'], x1=B, y1=f['z_top'], line=dict(color="gray", width=1.5, dash="dash"))
        fig.add_annotation(x=B/2, y=f['z_mid'], text=f"<b>ชั้น {f['floor']}</b>", showarrow=False)
        
        if not is_kn:
            val_w = f['p_w'] if mode == "External" else (f['net_w_c1'] if mode == "Case 1" else f['net_w_c2'])
            arr_len = max(2.0, min(3.5, 1.0 + abs(val_w)/30.0))
            draw_arrow(-arr_len, f['z_mid'], 0, f['z_mid'], val_w, "#DC2626", "right")
        else:
            net_story_force = f['force_c1'] if mode == "Case 1" else (f['force_c2'] if mode == "Case 2" else f['force_w_ext'] - f['force_l_ext'])
            arr_len = max(3.0, min(6.0, 2.0 + abs(net_story_force)/40.0))
            draw_arrow(-arr_len, f['z_top'], 0, f['z_top'], net_story_force, "#2563EB", "right")

    fig.update_layout(title=f"<b>แผนภาพจำลองแรงกระทำรายชั้น - โหมด {mode} ({unit_lbl})</b>", xaxis_title="B (ม.)", yaxis_title="z (ม.)", xaxis_range=[-10, B+10], yaxis_range=[-1, H_total + h_roof + 5], height=500, plot_bgcolor="white")
    return fig

# ==========================================
# INTERACTIVE TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 แผนภาพจำลองแรงลม (Visualizations)", "⚖️ วิเคราะห์แรงเฉือนฐาน (Base Shear)", "📑 เล่มรายการคำนวณและตาราง (Calculation)"])

with tab1:
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="card-stat"><p>ประเภทแรงลมกระโชก</p><h4 style="color:#0F766E;">{"พลศาสตร์ (Dynamic)" if "Flexible" in gust_mode else "คงที่ (Rigid)"}</h4></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="card-stat"><p>สัมประสิทธิ์ Cg ที่ใช้</p><h3>{Cg_final_used:.3f}</h3></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="card-stat"><p>ความสูงตึกรวม</p><h3>{H_total + h_roof:.2f} ม.</h3></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="card-stat"><p>แรงลมรวมฐาน (V_Wind)</p><h3 style="color:#2563EB;">{V_wind_max:.2f} kN</h3></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    view_opt = st.radio("🔘 **เลือกกรณีโหลด (Load Case):**", ["External", "Case 1", "Case 2"], horizontal=True)
    unit_opt = st.radio("📐 **เลือกหน่วยแสดงผลบนกราฟิก:**", ["kgf/m² (หน่วยแรงกระจาย)", "kN (แรงลัพธ์แบบจุด Point Load)"], horizontal=True)
    st.plotly_chart(plot_cross_section(floors_data, view_opt, unit_opt), use_container_width=True)

with tab2:
    st.markdown("#### ⚖️ การตรวจสอบและเปรียบเทียบแรงเฉือนที่ฐานอาคาร (Base Shear Comparison)")
    gov_force = "🌪️ WIND LOAD (แรงลมควบคุมการออกแบบ)" if V_wind_max > V_EQ_calc else "🚨 EARTHQUAKE LOAD (แรงแผ่นดินไหวควบคุม)"
    c_box = "#FEE2E2" if V_wind_max > V_EQ_calc else "#E0F2FE"
    c_border = "#EF4444" if V_wind_max > V_EQ_calc else "#0284C7"
    
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=["แรงลม Case 1", "แรงลม Case 2", "แรงแผ่นดินไหว (V_EQ)"], y=[V_wind_c1, V_wind_c2, V_EQ_calc],
                             marker_color=["#3B82F6", "#1D4ED8", "#EF4444"], text=[f"{V_wind_c1:.1f} kN", f"{V_wind_c2:.1f} kN", f"{V_EQ_calc:.1f} kN"], textposition='auto'))
    fig_bar.update_layout(height=400, plot_bgcolor="white")
    
    b1, b2 = st.columns([3, 2])
    with b1: st.plotly_chart(fig_bar, use_container_width=True)
    with b2:
        st.markdown(f'<div class="verdict-box" style="background-color:{c_box}; border-left:6px solid {c_border};">{gov_force}</div>', unsafe_allow_html=True)
        st.markdown(f"* **แรงลมสูงสุด ($V_{{Wind}}$):** `{V_wind_max:.2f}` kN\n* **แผ่นดินไหว ($V_{{EQ}}$):** `{V_EQ_calc:.2f}` kN\n* อัตราส่วน $V_{{Wind}} / V_{{EQ}}$ = **`{V_wind_max / max(V_EQ_calc, 1):.2f}`** เท่า")

with tab3:
    st.title("📑 รายการคำนวณแรงลมสุทธิโดยละเอียด (Meticulous Wind Load Report)")
    st.caption("อ้างอิงมาตรฐาน มยผ. 1311-50 มาตรฐานการคำนวณแรงลมและการตอบสนองของโครงสร้างอาคาร")
    st.markdown("---")
    
    st.subheader("1. พารามิเตอร์การออกแบบและสัมประสิทธิ์พลศาสตร์")
    c_inf1, c_inf2, c_inf3 = st.columns(3)
    with c_inf1:
        st.markdown(f"**ความเร็วลมออกแบบ (V):** `{V_input}` m/s")
        st.markdown(f"**สภาพภูมิประเทศ:** `{exposure}`")
        st.markdown(f"**ตัวคูณภูมิประเทศ (Ct):** `{Ct_input:.2f}`")
    with c_inf2:
        st.markdown(f"**มิติตัวตึก (B × L):** {B} ม. × {L} ม.")
        st.markdown(f"**ความสูงรวมอาคาร:** `{H_total + h_roof:.2f}` เมตร")
        st.markdown(f"**ลักษณะหลังคาอาคาร:** `{roof_type}`")
    with c_inf3:
        st.markdown(f"**โหมดการวิเคราะห์ Gust:** `{gust_mode}`")
        st.markdown(f"**สัมประสิทธิ์ ลมกระโชก ($C_g$):** $\\mathbf{{{Cg_final_used:.3f}}}$")

    # ส่วนแสดงพารามิเตอร์พลศาสตร์เจาะลึก
    if dyn_components:
        st.info("🧬 **รายละเอียดส่วนประกอบพลศาสตร์โครงสร้าง (Dynamic Component Breakdown):**")
        st.latex(r"I_{\bar{z}} = c \cdot \left(\frac{10}{z_{bar}}\right)^{1/6} = " + f"{dyn_components['Iz_bar']:.4f}")
        st.latex(r"Q = \sqrt{\frac{1}{1 + 0.63 \left(\frac{B+H}{L_{\bar{z}}}\right)^{0.63}}} = " + f"{dyn_components['Q']:.4f} \\quad [Background]")
        st.latex(r"R = \sqrt{\frac{1}{\beta} R_n R_h R_B (0.53 + 0.47 R_L)} = " + f"{dyn_components['R']:.4f} \\quad [Resonant]")
        st.markdown(f"👉 **การสั่นพ้องประสาน:** คาบการสั่นธรรมชาติ $T_1 = {T1_input}$ วินาที ความถี่ร่วม $n_1 = {1.0/T1_input:.2f}$ Hz, ตัวคูณลดทอนพลังงานสั่นสะเทือน $\\beta = {damping_input}$")

    st.markdown("<div style='border-top: 1px dashed #ddd; margin: 15px 0;'></div>", unsafe_allow_html=True)
    st.markdown(f"👉 **หน่วยแรงลมปะทะอ้างอิงพื้นฐาน ($q$):** $q = \\frac{{0.5 \\times 1.25 \\times {V_input}^2}}{{9.80665}} = \\mathbf{{{q:.3f}\\text{{ kgf/m}}^2}}$")

    st.subheader("2. ขั้นตอนการคำนวณและแทนค่ารายชั้น")
    for idx, f in enumerate(floors_data):
        q_z_mid = q * f['Ce'] * Ct_input
        if view_opt == "External": p_w_val = f['p_w']; p_l_val = p_leeward; f_w_val = f['force_w_ext']; f_l_val = f['force_l_ext']
        elif view_opt == "Case 1": p_w_val = f['net_w_c1']; p_l_val = net_l_c1; f_w_val = f['force_w_c1']; f_l_val = f['force_l_c1']
        else: p_w_val = f['net_w_c2']; p_l_val = net_l_c2; f_w_val = f['force_w_c2']; f_l_val = f['force_l_c2']
            
        net_f_story = f_w_val - f_l_val

        with st.expander(f"🔹 ชั้น {f['floor']} | พิกัดความสูง z = {f['z_bot']:.2f} ถึง {f['z_top']:.2f} ม. (โหมด: {view_opt})"):
            st.markdown(f"• **พื้นที่รับลมทางดิ่ง ($A$):** `{f['area_front']:.2f}` $m^2$")
            st.markdown(f"• **หน่วยแรงลมผิวหน้า ($p_{{windward}}$):** $(I_w \\times q_z \\times C_g \\times C_p) - p_{{int}} = \\mathbf{{{p_w_val:.2f}\\text{{ kgf/m}}^2}}$")
            st.markdown(f"• **แปลงเป็น Point Load แรงด้านข้างสุทธิของชั้นนี้:**")
            st.latex(r"F_{net} = (F_{windward} - F_{leeward}) = " + f"{net_f_story:.2f} \\text{{ kN}}")

    if "จั่ว" in roof_type:
        with st.expander(f"🔺 ส่วนเสริม: แรงเฉือนแนวราบจากหลังคาจั่ว (Roof Horizontal Shear)"):
            st.markdown(f"• แรงดันฝั่งรับลมหลังคา ($p_{{r,w}}$): `{p_roof_w:.2f}` kgf/m² | ฝั่งตามลม ($p_{{r,l}}$): `{p_roof_l:.2f}` kgf/m²")
            st.success(f"🎯 **แรงดันต่างแนวราบกดเข้าหัวเสาอาคาร:** $F_{{roof}} = {force_roof_horiz:.2f}$ kN")

    st.write("---")
    st.subheader("3. การสรุปผลแรงเฉือนรวมที่ฐานอาคาร (Total Base Shear Summary)")
    
    current_case_forces = [f['force_c1'] if view_opt == "Case 1" else (f['force_c2'] if view_opt == "Case 2" else f['force_w_ext'] - f['force_l_ext']) for f in floors_data]
    force_strings = [f"{force:.2f}" for force in current_case_forces]
    
    if "จั่ว" in roof_type:
        force_strings.append(f"{force_roof_horiz:.2f} (Roof Horizontal Force)")
        total_base_shear_current = sum(current_case_forces) + force_roof_horiz
    else:
        total_base_shear_current = sum(current_case_forces)

    equation_str = " + ".join(force_strings)
    st.markdown(f"📊 **สมการรวมแรงเฉือนแนวดิ่งฐานรากรากโครงสร้าง (กรณี {view_opt}):**")
    st.markdown(f"$$V_{{wind}} = \\sum F_{{net}} = {equation_str}$$")
    st.success(f"💥 **สรุปแรงเฉือนฐานรากสูงสุด:** $V_{{wind}} = \\mathbf{{{total_base_shear_current:.2f}\\text{{ kN}}}}$")
